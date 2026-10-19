import asyncio
import hashlib
import hmac
from datetime import date, datetime, timedelta, timezone
import json
import logging
import os
import re
import math
import secrets
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import bcrypt
import httpx
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure
from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

import foods
import kitchen
import kitchen_plan
import legal
import mailer
import vision

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.getenv("DB_NAME", "nutrimitra")
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
DEFAULT_TIMEZONE = "Asia/Kolkata"
MIN_AGE = 18  # Wellstride is for adults only
MAX_AGE = 100
AUTH_RATE_LIMIT = int(os.getenv("AUTH_RATE_LIMIT", "10"))
AUTH_RATE_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_WINDOW_MINUTES", "15")) * 60
# Local dev and the test suite call from loopback; set this to "" in production.
AUTH_RATE_LIMIT_EXEMPT_IPS = {ip.strip() for ip in os.getenv("AUTH_RATE_LIMIT_EXEMPT_IPS", "127.0.0.1,::1").split(",") if ip.strip()}
# Behind a reverse proxy (e.g. Render) the client IP is the first X-Forwarded-For entry.
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "").lower() in {"1", "true", "yes"}
# Browser origins allowed to call the API (comma separated). Unset means "this computer": the local web build on any
# port, because Expo moves to another port whenever 8081 is busy. The native app is not subject to CORS.
# Character classes, not backslashes, keep the dots and brackets literal.
LOCAL_ORIGIN_PATTERN = "^https?://(localhost|127[.]0[.]0[.]1|[[]::1[]])(:[0-9]+)?$"


def parse_origins(raw: str) -> List[str]:
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


CORS_ORIGINS = parse_origins(os.getenv("CORS_ORIGINS") or "")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
logger = logging.getLogger("nutrimitra")

# (collection, keys, options). Every query filters by user_id first, then by day or recency.
INDEXES = [
    ("users", [("id", ASCENDING)], {"unique": True, "name": "id_unique"}),
    ("profiles", [("user_id", ASCENDING)], {"name": "user_id"}),
    ("kitchens", [("user_id", ASCENDING)], {"name": "user_id_unique", "unique": True}),
    ("permissions", [("user_id", ASCENDING)], {"name": "user_id"}),
    ("reminders", [("user_id", ASCENDING)], {"name": "user_id"}),
    ("meals", [("user_id", ASCENDING), ("date", ASCENDING)], {"name": "user_date"}),
    ("meals", [("user_id", ASCENDING), ("created_at", DESCENDING)], {"name": "user_created"}),
    ("activities", [("user_id", ASCENDING), ("date", ASCENDING)], {"name": "user_date"}),
    ("activities", [("user_id", ASCENDING), ("created_at", DESCENDING)], {"name": "user_created"}),
    ("weights", [("user_id", ASCENDING), ("created_at", DESCENDING)], {"name": "user_created"}),
    ("coach_messages", [("user_id", ASCENDING), ("created_at", ASCENDING)], {"name": "user_created"}),
    ("plans", [("user_id", ASCENDING), ("updated_at", DESCENDING)], {"name": "user_updated"}),
    ("health_records", [("user_id", ASCENDING), ("start", ASCENDING)], {"name": "user_start"}),
    ("health_records", [("user_id", ASCENDING), ("external_id", ASCENDING), ("source", ASCENDING)], {"name": "user_external"}),
    ("password_resets", [("user_id", ASCENDING)], {"name": "user_id"}),
    # TTL: an expired reset code disappears on its own (and is checked again when used).
    ("password_resets", [("expires_at", ASCENDING)], {"name": "expires_ttl", "expireAfterSeconds": 0}),
    ("email_verifications", [("user_id", ASCENDING)], {"name": "user_id"}),
    ("email_verifications", [("expires_at", ASCENDING)], {"name": "expires_ttl", "expireAfterSeconds": 0}),
    ("user_sessions", [("session_token", ASCENDING)], {"name": "session_token"}),
    # TTL: MongoDB removes a session once expires_at (a BSON date) has passed.
    ("user_sessions", [("expires_at", ASCENDING)], {"name": "expires_ttl", "expireAfterSeconds": 0}),
]


# Every collection that holds a person's data by user_id. Account deletion clears all of them (then the users row itself);
# add new per-user collections here, and a test fails if one is missed.
USER_DATA_COLLECTIONS = ["profiles", "kitchens", "permissions", "reminders", "meals", "activities", "weights", "coach_messages", "plans", "health_records", "user_sessions", "password_resets", "email_verifications"]


async def ensure_email_index() -> bool:
    """Unique index on users.email. If existing data already has duplicates, report them and fall back to
    a plain index (data is never deleted); signups still guard with find-then-insert. Returns True if unique."""
    try:
        await db.users.create_index([("email", ASCENDING)], unique=True, name="email_unique")
        return True
    except (DuplicateKeyError, OperationFailure) as exc:
        duplicates = await db.users.aggregate([
            {"$group": {"_id": {"$toLower": "$email"}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
        ]).to_list(100)
        logger.error("users.email is not unique (%s); duplicates: %s. Created a non-unique index instead; resolve these accounts by hand.", exc, [(d["_id"], d["count"]) for d in duplicates])
        await db.users.create_index([("email", ASCENDING)], name="email")
        return False


async def migrate_session_expiry() -> int:
    """Older sessions stored expires_at as an ISO string, which a TTL index ignores; convert them to dates."""
    converted = 0
    async for session in db.user_sessions.find({"expires_at": {"$type": "string"}}, {"_id": 1, "expires_at": 1}):
        expiry = parse_expiry(session["expires_at"])
        if expiry:
            await db.user_sessions.update_one({"_id": session["_id"]}, {"$set": {"expires_at": expiry}})
            converted += 1
    return converted


async def ensure_indexes() -> None:
    """Idempotent: create_index is a no-op when an identical index already exists."""
    await ensure_email_index()
    for collection, keys, options in INDEXES:
        try:
            await db[collection].create_index(keys, **options)
        except OperationFailure as exc:
            logger.error("Could not create index %s on %s: %s", options.get("name"), collection, exc)
    converted = await migrate_session_expiry()
    if converted:
        logger.info("Converted %d session expiry values to dates", converted)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_indexes()
    yield
    client.close()


app = FastAPI(title="Wellstride API", version="1.0.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)


class AuthInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=80)


class SignupInput(AuthInput):
    # Required: "I am 18 or over and agree to the Terms and Privacy Policy". The server records the current version itself.
    accept_terms: bool = False


class ConsentInput(BaseModel):
    accept_terms: bool = False


class TokenResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class ProfileInput(BaseModel):
    age: int

    @field_validator("age")
    @classmethod
    def adult_age(cls, value: int) -> int:
        if value < MIN_AGE:
            raise PydanticCustomError("age_under_minimum", "You must be {min_age} or older to use Wellstride.", {"min_age": MIN_AGE})
        if value > MAX_AGE:
            raise PydanticCustomError("age_over_maximum", "Please enter an age of {max_age} or less.", {"max_age": MAX_AGE})
        return value

    sex: str = "Prefer not to say"
    height_cm: float = Field(gt=90, lt=240)
    weight_kg: float = Field(gt=25, lt=300)
    target_weight_kg: float = Field(gt=25, lt=300)
    conditions: List[str] = []
    dietary_preferences: List[str] = []
    allergies: List[str] = []
    disliked_foods: List[str] = []
    activity_level: str = "Moderately active"
    cooking_time: str = "20–30 min"
    food_budget: str = "Balanced"
    wellness_goal: str = "Healthier living"
    language: str = "en"
    timezone: str = Field(default=DEFAULT_TIMEZONE, max_length=64)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        # An unrecognised device timezone must not block onboarding; fall back to India.
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            return DEFAULT_TIMEZONE
        return value


class MealLogInput(BaseModel):
    meal_type: str
    name: str
    calories: int = Field(ge=0, le=3000)
    protein_g: float = Field(ge=0, le=300)
    carbs_g: float = Field(ge=0, le=400)
    fat_g: float = Field(ge=0, le=250)
    source: str = "manual"
    # What one serving was, e.g. "2 pieces (100 g)"; shown next to the meal. Optional.
    portion: Optional[str] = Field(default=None, max_length=80)


class MealPatchInput(BaseModel):
    meal_type: Optional[str] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    calories: Optional[int] = Field(default=None, ge=0, le=3000)
    protein_g: Optional[float] = Field(default=None, ge=0, le=300)
    carbs_g: Optional[float] = Field(default=None, ge=0, le=400)
    fat_g: Optional[float] = Field(default=None, ge=0, le=250)


class ActivityInput(BaseModel):
    activity_type: str
    duration_min: int = Field(ge=1, le=1440)
    distance_km: float = Field(default=0, ge=0, le=500)
    # Omit to have the server estimate it from duration and body weight.
    active_calories: Optional[int] = Field(default=None, ge=0, le=10000)
    source: str = "manual estimate"


class WeightInput(BaseModel):
    weight_kg: float = Field(gt=25, lt=300)


class CoachInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: str = "en"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def user_zone(profile: Optional[Dict[str, Any]]) -> ZoneInfo:
    """The user's timezone from their profile; India by default or when the stored value is unusable."""
    try:
        return ZoneInfo(str((profile or {}).get("timezone") or DEFAULT_TIMEZONE))
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def local_today(zone: ZoneInfo) -> date:
    return datetime.now(zone).date()


async def user_clock(user_id: str) -> tuple:
    """(profile, zone, today) for a user, so every "today" filter follows their local calendar."""
    profile = await db.profiles.find_one({"user_id": user_id}, {"_id": 0})
    zone = user_zone(profile)
    return profile, zone, local_today(zone)


def parse_expiry(value: Any) -> Optional[datetime]:
    """Session expiry as an aware UTC datetime, from a BSON date (read back naive) or a legacy ISO string."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class SlidingWindowLimiter:
    """In-memory sliding-window attempt counter, per process.

    Only record() and reset() are used by the app, so this can be swapped for a Redis or Mongo store
    with the same interface when the backend runs on more than one process."""

    def __init__(self, limit: int, window_seconds: int, clock=time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self.attempts: Dict[str, deque] = {}

    def record(self, key: str) -> Optional[int]:
        """Count one attempt. Returns seconds to wait if the key is over the limit (the attempt is not counted)."""
        now = self.clock()
        if len(self.attempts) > 10_000:
            # Bound memory: drop keys whose attempts have all aged out.
            self.attempts = {k: w for k, w in self.attempts.items() if w and w[-1] > now - self.window}
        window = self.attempts.setdefault(key, deque())
        while window and window[0] <= now - self.window:
            window.popleft()
        if len(window) >= self.limit:
            return max(1, math.ceil(window[0] + self.window - now))
        window.append(now)
        return None

    def reset(self, key: str) -> None:
        self.attempts.pop(key, None)


auth_limiter = SlidingWindowLimiter(AUTH_RATE_LIMIT, AUTH_RATE_WINDOW_SECONDS)
# Food search runs on every keystroke (after the app's debounce), so allow plenty per minute, per signed-in user.
FOODS_RATE_LIMIT = int(os.getenv("FOODS_RATE_LIMIT", "120"))
foods_limiter = SlidingWindowLimiter(FOODS_RATE_LIMIT, 60)


def client_ip(request: Request) -> str:
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded.strip():
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_auth_rate_limit(request: Request, action: str, email: Optional[str]) -> None:
    """Allow at most AUTH_RATE_LIMIT attempts per window per client IP and, when known, per email, for each action."""
    ip = client_ip(request)
    if ip in AUTH_RATE_LIMIT_EXEMPT_IPS:
        return
    keys = [f"{action}:ip:{ip}"] + ([f"{action}:email:{email}"] if email else [])
    waits = [wait for wait in (auth_limiter.record(key) for key in keys) if wait]
    if waits:
        minutes = max(1, math.ceil(max(waits) / 60))
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Please wait {minutes} minute{'s' if minutes != 1 else ''} and try again.",
            headers={"Retry-After": str(max(waits))},
        )


def is_email_verified(doc: Dict[str, Any]) -> bool:
    """Google vouches for its accounts' emails (they have no password); everyone else proves theirs with a code."""
    return doc.get("email_verified") is True or not doc.get("password_hash")


def public_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": doc.get("id", ""),
        "email": doc.get("email", ""),
        "name": doc.get("name", ""),
        "language": doc.get("language", "en"),
        "onboarding_complete": bool(doc.get("onboarding_complete", False)),
        "email_verified": is_email_verified(doc),
        # Google-created accounts have no password; deleting one is confirmed with the word DELETE alone.
        "has_password": bool(doc.get("password_hash")),
        "consent_version": doc.get("consent_version"),
        # Accounts from before consent existed, or from before the policies last changed, are asked once on next launch.
        "needs_consent": doc.get("consent_version") != legal.CONSENT_VERSION,
    }


def issue_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": int(now.timestamp()), "exp": now + timedelta(hours=JWT_EXPIRE_HOURS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue")
    user_id: Optional[str] = None
    issued_at = 0
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        issued_at = int(payload.get("iat") or 0)
    except jwt.PyJWTError:
        session = await db.user_sessions.find_one({"session_token": credentials.credentials}, {"_id": 0})
        expiry = parse_expiry((session or {}).get("expires_at"))
        # The TTL monitor runs about once a minute, so check expiry here as well.
        if session and expiry and expiry > datetime.now(timezone.utc):
            user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    # A password reset signs every earlier token out (they were issued before the change).
    if user.get("password_changed_at") and issued_at < int(user["password_changed_at"]):
        raise HTTPException(status_code=401, detail="Session expired")
    return user


@api_router.get("/")
async def root():
    return {"name": "Wellstride", "status": "ready", "ai_provider": "groq", "ai_model": GROQ_MODEL, "vision": vision.status()}


@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(payload: SignupInput, request: Request, background: BackgroundTasks):
    email = payload.email.lower()
    check_auth_rate_limit(request, "signup", email)
    require_consent(payload.accept_terms)
    if await db.users.find_one({"email": email}, {"_id": 0}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": payload.name.strip() or email.split("@")[0].title(),
        "password_hash": bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode(),
        "language": "en",
        "onboarding_complete": False,
        "created_at": now_iso(),
        **consent_fields(),
    }
    try:
        await db.users.insert_one(user)
    except DuplicateKeyError as exc:
        # Two signups for the same email raced past the check above; the unique index caught it.
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    await start_email_verification(user, background)
    return {"token": issue_token(user["id"]), "user": public_user(user)}


def require_consent(accepted: bool) -> None:
    if accepted is not True:
        raise HTTPException(status_code=422, detail={"code": "consent_required", "message": "Please confirm that you are 18 or over and agree to the Terms and Privacy Policy."})


def consent_fields() -> Dict[str, Any]:
    return {"consent_version": legal.CONSENT_VERSION, "consent_at": now_iso()}


VERIFY_MINUTES = 60
VERIFY_MAX_WRONG_CODES = 5
VERIFY_INVALID = "That code is invalid or has expired. Please request a new one."


class VerifyInput(BaseModel):
    code: str = Field(min_length=4, max_length=20)


async def start_email_verification(user: Dict[str, Any], background: BackgroundTasks) -> None:
    """Replaces any earlier code with a new 6 digit one and emails it (after the response, so a slow mail server never delays it)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    await db.email_verifications.delete_many({"user_id": user["id"]})
    await db.email_verifications.insert_one({
        "user_id": user["id"],
        "code_hash": hash_code(code),
        "attempts": 0,
        "created_at": now_iso(),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=VERIFY_MINUTES),
    })
    text = "\n".join([
        f"Your Wellstride verification code is: {code}",
        "",
        f"Enter it in the app to confirm your email. It expires in {VERIFY_MINUTES} minutes. If you did not create a Wellstride account, ignore this email.",
        "",
    ])
    background.add_task(mailer.send_email, user["email"], "Your Wellstride verification code", text)


@api_router.post("/auth/resend-verification")
async def resend_verification(request: Request, background: BackgroundTasks, user: Dict[str, Any] = Depends(current_user)):
    check_auth_rate_limit(request, "resend", user["email"])
    if is_email_verified(user):
        return {"ok": True, "already_verified": True}
    await start_email_verification(user, background)
    return {"ok": True, "already_verified": False}


@api_router.post("/auth/verify-email")
async def verify_email(payload: VerifyInput, request: Request, user: Dict[str, Any] = Depends(current_user)):
    check_auth_rate_limit(request, "verify", user["email"])
    if is_email_verified(user):
        return {"ok": True, "user": public_user(user)}
    record = await db.email_verifications.find_one({"user_id": user["id"]})
    accepted = False
    if record:
        expiry = parse_expiry(record.get("expires_at"))
        if expiry and expiry > datetime.now(timezone.utc):
            if hmac.compare_digest(str(record.get("code_hash")), hash_code(payload.code)):
                accepted = await db.email_verifications.find_one_and_delete({"_id": record["_id"]}) is not None
            elif int(record.get("attempts", 0)) + 1 >= VERIFY_MAX_WRONG_CODES:
                await db.email_verifications.delete_one({"_id": record["_id"]})
            else:
                await db.email_verifications.update_one({"_id": record["_id"]}, {"$inc": {"attempts": 1}})
    if not accepted:
        raise HTTPException(status_code=400, detail=VERIFY_INVALID)
    await db.users.update_one({"id": user["id"]}, {"$set": {"email_verified": True}})
    return {"ok": True, "user": public_user({**user, "email_verified": True})}


def password_matches(password: str, stored_hash: Any) -> bool:
    """bcrypt check that treats a missing or malformed hash (e.g. Google-created accounts) as a mismatch."""
    if not stored_hash or not isinstance(stored_hash, str):
        return False
    try:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except ValueError:
        return False


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(payload: AuthInput, request: Request):
    email = payload.email.lower()
    check_auth_rate_limit(request, "login", email)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not password_matches(payload.password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    # A successful sign-in clears the account's counter; the per-IP counter keeps running.
    auth_limiter.reset(f"login:email:{email}")
    return {"token": issue_token(user["id"]), "user": public_user(user)}


RESET_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I, so a code read from an email is hard to mistype
RESET_CODE_LENGTH = 8
RESET_MINUTES = 30
RESET_MAX_WRONG_CODES = 5
FORGOT_MESSAGE = "If an account exists for this email, we have sent a reset code. It works for 30 minutes."
RESET_INVALID = "That code is invalid or has expired. Please request a new one."


class ForgotInput(BaseModel):
    email: EmailStr


class ResetInput(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=40)
    new_password: str = Field(min_length=8, max_length=128)


def normalize_code(code: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", code).upper()


def hash_code(code: str) -> str:
    """Codes are stored only as a keyed hash, so a copy of the database cannot be used to reset anyone's password."""
    return hmac.new(JWT_SECRET.encode(), normalize_code(code).encode(), hashlib.sha256).hexdigest()


def reset_email_text(email: str, code: str) -> str:
    from urllib.parse import quote

    link = f"wellstride://reset-password?email={quote(email)}&code={code}"
    lines = [
        f"Your Wellstride password reset code is: {code}",
        "",
        "Open the app and enter it on the Reset password screen, or open this link on your phone:",
        link,
        "",
        f"The code works once and expires in {RESET_MINUTES} minutes. If you did not ask for this, ignore this email; your password has not changed.",
    ]
    return "\n".join(lines) + "\n"


@api_router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotInput, request: Request, background: BackgroundTasks):
    """Always answers the same way, whether or not the email has an account (no account enumeration)."""
    email = payload.email.lower()
    check_auth_rate_limit(request, "forgot", email)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    # Only verified emails get a code: an unverified address may belong to someone else. The answer is the same either way.
    if user and user.get("password_hash") and is_email_verified(user):
        code = "".join(secrets.choice(RESET_CODE_ALPHABET) for _ in range(RESET_CODE_LENGTH))
        await db.password_resets.delete_many({"user_id": user["id"]})  # a new request replaces any earlier code
        await db.password_resets.insert_one({
            "user_id": user["id"],
            "code_hash": hash_code(code),
            "attempts": 0,
            "created_at": now_iso(),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=RESET_MINUTES),
        })
        # Sent after the response goes out, so the time taken does not tell anyone whether the account exists.
        background.add_task(mailer.send_email, email, "Your Wellstride password reset code", reset_email_text(email, code))
    return {"ok": True, "message": FORGOT_MESSAGE}


@api_router.post("/auth/reset-password")
async def reset_password(payload: ResetInput, request: Request):
    email = payload.email.lower()
    check_auth_rate_limit(request, "reset", email)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    record = await db.password_resets.find_one({"user_id": user["id"]}) if user else None
    accepted = False
    if record:
        expiry = parse_expiry(record.get("expires_at"))
        if expiry and expiry > datetime.now(timezone.utc):
            if hmac.compare_digest(str(record.get("code_hash")), hash_code(payload.code)):
                # Deleting the record is what spends the code: only one request can ever get it back.
                accepted = await db.password_resets.find_one_and_delete({"_id": record["_id"]}) is not None
            elif int(record.get("attempts", 0)) + 1 >= RESET_MAX_WRONG_CODES:
                await db.password_resets.delete_one({"_id": record["_id"]})
            else:
                await db.password_resets.update_one({"_id": record["_id"]}, {"$inc": {"attempts": 1}})
    if not accepted:
        raise HTTPException(status_code=400, detail=RESET_INVALID)
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "password_hash": bcrypt.hashpw(payload.new_password.encode(), bcrypt.gensalt()).decode(),
        "password_changed_at": int(datetime.now(timezone.utc).timestamp()),
    }})
    await db.password_resets.delete_many({"user_id": user["id"]})
    await db.user_sessions.delete_many({"user_id": user["id"]})
    auth_limiter.reset(f"login:email:{email}")
    return {"ok": True}


GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"


class GoogleInput(BaseModel):
    id_token: str = Field(min_length=20, max_length=4000)
    # The app sends the nonce it put in the sign-in request; the token must carry the same one.
    nonce: Optional[str] = Field(default=None, max_length=200)
    # Needed the first time (when the account is created); an existing account is asked separately via POST /consent.
    accept_terms: bool = False


def google_client_ids() -> List[str]:
    """OAuth client IDs this server accepts ID tokens for (GOOGLE_CLIENT_IDS, comma separated; GOOGLE_CLIENT_ID also works).
    Empty means Google sign-in is switched off."""
    raw = os.getenv("GOOGLE_CLIENT_IDS") or os.getenv("GOOGLE_CLIENT_ID") or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


def verify_google_id_token_sync(token: str, client_ids: List[str], nonce: Optional[str] = None) -> Dict[str, Any]:
    """Check an ID token's signature (against Google's public certs), audience, issuer, expiry and nonce.
    Raises ValueError if anything is off; returns the verified claims."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    claims = google_id_token.verify_token(token, google_requests.Request(), audience=client_ids, certs_url=os.getenv("GOOGLE_CERTS_URL") or GOOGLE_CERTS_URL, clock_skew_in_seconds=10)
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise ValueError("Wrong token issuer")
    if nonce is not None and claims.get("nonce") != nonce:
        raise ValueError("Nonce does not match")
    return dict(claims)


async def verify_google_id_token(token: str, client_ids: List[str], nonce: Optional[str] = None) -> Dict[str, Any]:
    """The one place Google verification happens (it fetches certificates over the network, so it runs off the
    event loop). Tests replace this function with a fake verifier."""
    return await asyncio.to_thread(verify_google_id_token_sync, token, client_ids, nonce)


@api_router.post("/auth/google", response_model=TokenResponse)
async def auth_google(payload: GoogleInput, request: Request):
    """Sign in with a Google ID token obtained by the app. Accounts are matched on the verified email, so a
    Google-created account from before keeps working, and a person with an email account signs into that account."""
    check_auth_rate_limit(request, "google", None)
    client_ids = google_client_ids()
    if not client_ids:
        raise HTTPException(status_code=503, detail={"code": "google_not_configured", "message": "Google sign-in isn't set up yet. Please use your email and password."})
    try:
        claims = await verify_google_id_token(payload.id_token, client_ids, payload.nonce)
    except Exception as exc:  # google-auth raises ValueError or GoogleAuthError subclasses
        logger.info("Google ID token rejected: %s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified") from exc
    email = str(claims.get("email") or "").strip().lower()
    if not email or claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        require_consent(payload.accept_terms)
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": str(claims.get("name") or email.split("@")[0]).strip().title()[:80],
            "picture": str(claims.get("picture") or "")[:500],
            "password_hash": "",
            "email_verified": True,
            "language": "en",
            "onboarding_complete": False,
            "created_at": now_iso(),
            **consent_fields(),
        }
        try:
            await db.users.insert_one(user)
        except DuplicateKeyError:
            # A concurrent sign-in created the account first; use that one.
            user = await db.users.find_one({"email": email}, {"_id": 0})
    return {"token": issue_token(user["id"]), "user": public_user(user)}


@api_router.post("/consent")
async def accept_consent(payload: ConsentInput, user: Dict[str, Any] = Depends(current_user)):
    """Records agreement to the current Terms and Privacy Policy (existing accounts are asked once)."""
    require_consent(payload.accept_terms)
    fields = consent_fields()
    await db.users.update_one({"id": user["id"]}, {"$set": fields})
    return {"user": public_user({**user, **fields})}


class DeleteAccountInput(BaseModel):
    confirm: str = ""
    password: str = Field(default="", max_length=128)


@api_router.delete("/account")
async def delete_account(payload: DeleteAccountInput, request: Request, user: Dict[str, Any] = Depends(current_user)):
    """Permanently deletes the signed-in person and everything stored about them.

    Confirmation: the word DELETE, plus the password for accounts that have one (Google accounts have none, so the word
    alone confirms them). Tokens stop working at once because current_user no longer finds the account."""
    check_auth_rate_limit(request, "delete-account", user.get("email"))
    if payload.confirm.strip() != "DELETE":
        raise HTTPException(status_code=422, detail="Type DELETE to confirm.")
    if user.get("password_hash") and not password_matches(payload.password, user.get("password_hash")):
        raise HTTPException(status_code=403, detail="Password is incorrect")
    removed: Dict[str, int] = {}
    for name in USER_DATA_COLLECTIONS:
        removed[name] = (await db[name].delete_many({"user_id": user["id"]})).deleted_count
    await db.users.delete_one({"id": user["id"]})
    logger.info("Deleted account %s (%s)", user["id"], ", ".join(f"{name}={count}" for name, count in removed.items() if count))
    return {"ok": True}


@api_router.get("/me")
async def me(user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"user": public_user(user), "profile": profile}


@api_router.put("/profile")
async def save_profile(payload: ProfileInput, user: Dict[str, Any] = Depends(current_user)):
    profile = payload.model_dump()
    profile.update({"user_id": user["id"], "updated_at": now_iso()})
    await db.profiles.update_one({"user_id": user["id"]}, {"$set": profile}, upsert=True)
    await db.users.update_one({"id": user["id"]}, {"$set": {"onboarding_complete": True, "language": payload.language}})
    return {"profile": profile}


class KitchenInput(BaseModel):
    items: List[str] = Field(default_factory=list, max_length=kitchen.MAX_ITEMS)
    meals_per_day: int = Field(default=3, ge=kitchen.MIN_MEALS, le=kitchen.MAX_MEALS)
    household_size: int = Field(default=2, ge=kitchen.MIN_PEOPLE, le=kitchen.MAX_PEOPLE)
    cooking_time: Optional[str] = None

    @field_validator("cooking_time")
    @classmethod
    def known_cooking_time(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in kitchen.COOKING_TIMES:
            raise ValueError("Pick one of the cooking times offered.")
        return value


def public_kitchen(doc: Optional[Dict[str, Any]], profile: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The saved kitchen as the app sees it. Items that no longer fit the diet (it may have changed since) are left out."""
    if not doc:
        return None
    allowed = {item.id for item in kitchen.catalogue.visible((profile or {}).get("dietary_preferences", []), kitchen.profile_exclusions(profile))}
    return {
        "items": [iid for iid in doc.get("items", []) if iid in allowed],
        "meals_per_day": doc.get("meals_per_day", 3),
        "household_size": doc.get("household_size", 2),
        "cooking_time": doc.get("cooking_time"),
        "updated_at": doc.get("updated_at"),
    }


@api_router.get("/kitchen/ingredients")
async def kitchen_ingredients(q: str = "", diet: Optional[str] = None, exclude: Optional[str] = None, user: Dict[str, Any] = Depends(current_user)):
    """The ingredients this person may pick, by group. `diet` and `exclude` (comma separated) stand in for the saved profile,
    which does not exist yet while they are still in onboarding."""
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    preferences = [part for part in diet.split(",")] if diet is not None else profile.get("dietary_preferences", [])
    exclusions = [part for part in exclude.split(",")] if exclude is not None else kitchen.profile_exclusions(profile)
    visible = kitchen.catalogue.search(kitchen.catalogue.visible(preferences, exclusions), q[:60])
    return {"groups": kitchen.GROUPS, "ingredients": [item.public() for item in visible]}


@api_router.get("/kitchen")
async def get_kitchen(user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    doc = await db.kitchens.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"configured": doc is not None, "kitchen": public_kitchen(doc, profile)}


@api_router.put("/kitchen")
async def put_kitchen(payload: KitchenInput, user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    items, problems = kitchen.clean_kitchen_items(payload.items, (profile or {}).get("dietary_preferences", []), kitchen.profile_exclusions(profile))
    if problems:
        raise HTTPException(status_code=422, detail=problems[0])
    doc = {"user_id": user["id"], "items": items, "meals_per_day": payload.meals_per_day, "household_size": payload.household_size, "cooking_time": payload.cooking_time, "updated_at": now_iso()}
    await db.kitchens.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    return {"configured": True, "kitchen": public_kitchen(doc, profile)}


# What "Export my data" returns: everything stored about the person except sign-in secrets, sessions and one-time codes.
EXPORT_COLLECTIONS = ["profiles", "kitchens", "permissions", "reminders", "meals", "activities", "weights", "coach_messages", "plans", "health_records"]


@api_router.get("/account/export")
async def export_account(request: Request, user: Dict[str, Any] = Depends(current_user)):
    check_auth_rate_limit(request, "export", user.get("email"))
    data: Dict[str, Any] = {"exported_at": now_iso(), "user": public_user(user)}
    for name in EXPORT_COLLECTIONS:
        data[name] = await db[name].find({"user_id": user["id"]}, {"_id": 0, "user_id": 0}).to_list(5000)
    return data


def calorie_target(profile: Dict[str, Any]) -> int:
    """Daily energy estimate: Mifflin-St Jeor x activity factor, adjusted for the goal, floored at 1,200 kcal."""
    weight = float(profile.get("weight_kg") or 70)
    height = float(profile.get("height_cm") or 165)
    age = int(profile.get("age") or 30)
    sex_adjust = 5 if profile.get("sex") == "Male" else -161 if profile.get("sex") == "Female" else -78
    activity_factor = {"Lightly active": 1.4, "Moderately active": 1.55, "Very active": 1.7}.get(str(profile.get("activity_level", "")), 1.5)
    goal_adjust = {"Weight loss": -400, "Weight gain": 300, "Muscle building": 250}.get(str(profile.get("wellness_goal", "")), 0)
    return max(1200, int(((10 * weight) + (6.25 * height) - (5 * age) + sex_adjust) * activity_factor + goal_adjust))


MEAL_SHARES = {"breakfast": 0.25, "lunch": 0.35, "snack": 0.10, "dinner": 0.30}
MEAL_FAT_SHARES = {"breakfast": 0.28, "lunch": 0.27, "snack": 0.35, "dinner": 0.27}
# Small day-to-day swing so a fallback week does not repeat identical numbers; averages to ~1.0.
DAY_FACTORS = (1.0, 0.95, 1.04, 0.98, 1.03, 0.96, 1.04)


def portion_for(profile: Dict[str, Any], meal: str, day_index: int = 0) -> Dict[str, Any]:
    """Fallback meal nutrition sized from the user's daily target, the meal's share of the day and the goal."""
    goal = profile.get("wellness_goal", "Healthier living")
    protein_share = 0.25 if goal in {"Muscle building", "Weight gain", "Weight loss"} else 0.20
    fat_share = MEAL_FAT_SHARES.get(meal, 0.28)
    calories = int(round(calorie_target(profile) * MEAL_SHARES.get(meal, 0.25) * DAY_FACTORS[day_index % len(DAY_FACTORS)] / 5) * 5)
    portions = {"breakfast": "1 bowl", "lunch": "1 balanced plate", "snack": "1 small bowl", "dinner": "1 plate"}
    return {
        "portion": portions.get(meal, "1 serving"),
        "protein_g": round(calories * protein_share / 4),
        "carbs_g": round(calories * (1 - protein_share - fat_share) / 4),
        "fat_g": round(calories * fat_share / 9),
        "calories": calories,
    }


def local_plan(profile: Dict[str, Any]) -> Dict[str, Any]:
    vegetarian = "Vegetarian" in profile.get("dietary_preferences", [])
    protein = "paneer bhurji" if vegetarian else "masala egg bhurji"
    days = []
    rotation = [
        ("Moong dal chilla", "Rajma quinoa bowl", "Vegetable khichdi"),
        ("Overnight oats with chia", "Paneer tikka wrap", "Tofu stir-fry"),
        ("Idli with sambar", "Millet pulao with raita", "Dal palak with roti"),
        ("Besan cheela", "Chole salad bowl", "Lemon rice with eggs"),
        ("Poha with peanuts", "Avocado paneer toast", "Vegetable soup with tofu"),
        ("Greek yogurt fruit bowl", "Brown rice dal plate", "Stuffed veg paratha"),
        ("Oats upma", "Chickpea lettuce wraps", "Paneer bhurji with roti"),
    ]
    for index, (breakfast, lunch, dinner) in enumerate(rotation, 1):
        if not vegetarian and index % 3 == 0:
            breakfast = protein
        meals = []
        for meal_type, name in [("breakfast", breakfast), ("lunch", lunch), ("snack", "Fruit, almonds & pumpkin seeds"), ("dinner", dinner)]:
            nutrition = portion_for(profile, meal_type, index - 1)
            meals.append({"type": meal_type, "name": name, **nutrition, "logged": False})
        days.append({"day": index, "title": f"Day {index}", "focus": "Protein + fibre balance", "meals": meals})
    return {"goal": profile.get("wellness_goal", "Healthier living"), "days": days, "generated_by": "Wellstride nutrition engine", "updated_at": now_iso()}


AI_BUSY_MESSAGE = "The AI is busy right now. Please try again in a minute."
AI_UNAVAILABLE_MESSAGE = "The AI is unavailable right now. Please try again later."
AI_RETRY_DELAYS = (1.0, 2.0)  # exponential backoff: at most 2 retries after the first attempt
AI_RETRY_STATUSES = {429, 503}  # rate limited / over capacity


class AIUnavailable(Exception):
    """The AI provider could not answer. code is "ai_busy" (rate limited) or "ai_unavailable"."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def ai_error(exc: AIUnavailable) -> HTTPException:
    """Structured error the app turns into a friendly message instead of a canned reply."""
    return HTTPException(status_code=503, detail={"code": exc.code, "message": exc.message}, headers={"Retry-After": "60"})


def retry_delay(response: httpx.Response, attempt: int) -> float:
    """Backoff for this attempt, honouring a short Retry-After from the provider."""
    try:
        suggested = float(response.headers.get("retry-after", ""))
    except ValueError:
        suggested = 0.0
    return min(max(AI_RETRY_DELAYS[attempt], suggested), 10.0)


async def groq_chat(messages: List[Dict[str, str]], user_id: str, max_tokens: int = 2000) -> str:
    """Single swappable Groq chat call used by every AI surface.

    Returns "" only when no API key is configured. Rate limits and empty replies are retried with backoff;
    if the provider still cannot answer, raises AIUnavailable."""
    if not GROQ_API_KEY:
        return ""
    body = {"model": GROQ_MODEL, "temperature": 0.4, "max_tokens": max_tokens, "messages": messages}
    for attempt in range(len(AI_RETRY_DELAYS) + 1):
        try:
            async with httpx.AsyncClient(timeout=35) as http:
                response = await http.post(f"{GROQ_BASE_URL}/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=body)
        except httpx.HTTPError as exc:
            logger.warning("Groq request failed for %s: %s", user_id, exc)
            raise AIUnavailable("ai_unavailable", AI_UNAVAILABLE_MESSAGE) from exc
        if response.status_code in AI_RETRY_STATUSES:
            if attempt < len(AI_RETRY_DELAYS):
                delay = retry_delay(response, attempt)
                logger.info("Groq returned %s for %s; retrying in %.1fs", response.status_code, user_id, delay)
                await asyncio.sleep(delay)
                continue
            logger.warning("Groq still returning %s for %s after %d retries", response.status_code, user_id, len(AI_RETRY_DELAYS))
            raise AIUnavailable("ai_busy", AI_BUSY_MESSAGE)
        if response.status_code >= 400:
            logger.warning("Groq request failed for %s: HTTP %s", user_id, response.status_code)
            raise AIUnavailable("ai_unavailable", AI_UNAVAILABLE_MESSAGE)
        try:
            content = response.json()["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning("Groq returned an unreadable response for %s: %s", user_id, exc)
            raise AIUnavailable("ai_unavailable", AI_UNAVAILABLE_MESSAGE) from exc
        if content.strip():
            return content
        # Reasoning models sometimes spend the whole token budget thinking and return nothing; try again.
        if attempt < len(AI_RETRY_DELAYS):
            logger.info("Groq returned an empty reply for %s; retrying", user_id)
            await asyncio.sleep(AI_RETRY_DELAYS[attempt])
            continue
        logger.warning("Groq returned an empty reply for %s after %d retries", user_id, len(AI_RETRY_DELAYS))
        raise AIUnavailable("ai_unavailable", AI_UNAVAILABLE_MESSAGE)
    raise AIUnavailable("ai_busy", AI_BUSY_MESSAGE)


async def groq_text(system: str, prompt: str, user_id: str) -> str:
    return await groq_chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}], user_id)


PLAN_SYSTEM = (
    "You are Wellstride's Indian nutrition planning engine. Return ONLY valid JSON, no markdown: "
    '{"days": [{"day": 1, "title": str, "focus": str, "meals": [{"type": "breakfast"|"lunch"|"snack"|"dinner", "name": str, "portion": str, '
    '"calories": int, "protein_g": number, "carbs_g": number, "fat_g": number}]}, ...], "reasoning": str} — exactly 7 days, exactly 4 meals '
    "(breakfast, lunch, snack, dinner) per day. Rules: Indian-first meals with global nutritious ingredients where helpful; strictly respect "
    "dietary preferences, allergies and disliked foods; match cooking time and budget; balance protein, fibre and healthy fats; avoid repeating "
    "meals the user logged recently. The context lists the user's self-reported health_conditions: favour generally sensible food choices for "
    "them (for example, steady-carbohydrate and lower-sugar meals when diabetes or PCOS is listed, lower-salt meals for blood pressure) but treat "
    "them only as user-provided information, never as a diagnosis. This is general wellness guidance, not medical advice: do not claim the plan is "
    "medically tailored, prescribed or safe for a condition, and never mention medicines or doses. In the reasoning and meal names, never name a "
    "condition or say the plan supports, manages, treats or suits it; describe only the food itself (for example 'lower-sugar, high-fibre meals')."
)


KITCHEN_PLAN_SYSTEM = (
    PLAN_SYSTEM
    + " The user message also lists kitchen_items (what the person has at home), extra_items_allowed (other ingredients you may add), "
    "max_extra_items, cooked_meals (the meals cooked at home; any other main meal must need no real cooking), cooking_time_cap_minutes and household_size. "
    "Build every meal from kitchen_items first, plus the pantry basics (salt, spices, ginger, garlic, chillies, tamarind, curry leaves, coriander, "
    "lemon, cooking oil). Across the WHOLE week use at most max_extra_items different ingredients from extra_items_allowed, and never any other ingredient. "
    'Each meal also has "ingredients": the main ingredients it uses, written exactly as named in kitchen_items or extra_items_allowed (not the pantry basics). '
    "Vary the meals and keep each within the cooking time."
)


def health_conditions(profile: Dict[str, Any]) -> List[str]:
    """The user's self-reported conditions, cleaned for use in a prompt."""
    raw = profile.get("conditions") or []
    if isinstance(raw, str):
        raw = raw.split(",")
    return [str(item).strip()[:60] for item in raw if str(item).strip()][:10]


CONDITION_STOPWORDS = {"type", "with", "high", "low", "chronic", "issue", "issues", "problem", "problems", "disease", "syndrome", "condition", "conditions"}


def condition_terms(profile: Dict[str, Any]) -> List[str]:
    """Lowercase phrases and words that identify the user's stated conditions in generated text."""
    terms = set()
    for condition in health_conditions(profile):
        lowered = condition.lower()
        terms.add(lowered)
        # Long words are cut to a 6-letter stem so "diabetic" matches "diabetes".
        terms |= {word[:6] for word in re.findall(r"[a-z]{4,}", lowered) if word not in CONDITION_STOPWORDS}
    return sorted(terms, key=len, reverse=True)


def mentions_condition(text: str, profile: Dict[str, Any]) -> bool:
    lowered = str(text).lower()
    # Match at the start of a word, so "high" in "high-fibre" does not count for a condition called "high ...".
    word_start = chr(92) + "b"
    return any(re.search(word_start + re.escape(term), lowered) for term in condition_terms(profile))


def strip_condition_claims(plan: Dict[str, Any], profile: Dict[str, Any], fallback: Dict[str, Any]) -> None:
    """The prompt asks the model not to name a user's condition or claim the plan suits it. If it does anyway,
    swap that text (the plan reasoning and each day's focus) for neutral wording, so the app never shows a
    medical claim."""
    if not condition_terms(profile):
        return
    if mentions_condition(plan.get("reasoning", ""), profile):
        plan["reasoning"] = fallback.get("reasoning", "")
    for day in plan.get("days", []):
        if mentions_condition(day.get("focus", ""), profile):
            day["focus"] = "Balanced nutrition"


def plan_context(profile: Dict[str, Any], meals: List[Dict[str, Any]], activities: List[Dict[str, Any]], weights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """What the plan generator is told about the user, with health conditions stated explicitly."""
    return {
        "profile": profile,
        "health_conditions": health_conditions(profile),
        "recent_meals_logged": [str(item.get("name", ""))[:40] for item in meals[-14:]],
        "activity_sessions_last_7_days": len(activities),
        "recent_weights_kg": [item.get("weight_kg") for item in weights[:7]],
    }


NON_VEG_KEYWORDS = ("chicken", "mutton", "fish", "egg", "eggs", "prawn", "shrimp", "beef", "pork", "meat", "keema", "lamb", "crab", "tuna", "salmon", "bacon", "sausage", "anchovy", "anchovies")
NON_VEGAN_EXTRA_KEYWORDS = ("paneer", "cheese", "curd", "yogurt", "yoghurt", "ghee", "butter", "milk", "cream", "honey")


def plan_restriction_violations(days: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[str]:
    """Server-side safety net: an AI-generated plan can ignore the prompt's dietary
    instructions, so re-check every meal name against the profile's stated
    preferences, allergies and dislikes before trusting it."""
    prefs = {str(p).lower() for p in profile.get("dietary_preferences", [])}
    banned = set()
    if "vegetarian" in prefs or "vegan" in prefs:
        banned |= {w.lower() for w in NON_VEG_KEYWORDS}
    if "vegan" in prefs:
        banned |= {w.lower() for w in NON_VEGAN_EXTRA_KEYWORDS}
    banned |= {str(a).lower().strip() for a in profile.get("allergies", []) if str(a).strip()}
    banned |= {str(d).lower().strip() for d in profile.get("disliked_foods", []) if str(d).strip()}
    if not banned:
        return []
    offenders = []
    for day in days:
        for meal in day.get("meals", []):
            name = str(meal.get("name", "")).lower()
            if any(re.search(rf"\b{re.escape(word)}s?\b", name) for word in banned):
                offenders.append(meal.get("name", ""))
    return offenders


def coerce_plan(candidate: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an AI-generated plan; any structural problem falls back to the deterministic engine."""
    days = candidate.get("days")
    if not isinstance(days, list) or len(days) < 7:
        return fallback
    cleaned = []
    for index, day in enumerate(days[:7], 1):
        meals = day.get("meals") if isinstance(day, dict) else None
        if not isinstance(meals, list) or len(meals) < 4:
            return fallback
        safe_meals = []
        for meal in meals[:4]:
            try:
                safe_meals.append({
                    "type": str(meal.get("type") or "snack")[:20],
                    "name": str(meal.get("name") or "Balanced meal")[:80],
                    "portion": str(meal.get("portion") or "1 serving")[:60],
                    "calories": max(0, min(1500, int(meal.get("calories") or 400))),
                    "protein_g": max(0, min(150, float(meal.get("protein_g") or 20))),
                    "carbs_g": max(0, min(200, float(meal.get("carbs_g") or 45))),
                    "fat_g": max(0, min(120, float(meal.get("fat_g") or 15))),
                    "ingredients": [str(item)[:40] for item in meal["ingredients"][:12]] if isinstance(meal.get("ingredients"), list) else None,
                    "logged": False,
                })
            except (TypeError, ValueError, AttributeError):
                return fallback
        cleaned.append({"day": index, "title": str(day.get("title") or f"Day {index}")[:40], "focus": str(day.get("focus") or "Balanced nutrition")[:80], "meals": safe_meals})
    return {"goal": fallback["goal"], "days": cleaned, "reasoning": str(candidate.get("reasoning") or fallback.get("reasoning", ""))[:600], "generated_by": "groq adaptive engine", "updated_at": now_iso()}


def kitchen_plan_problems(days: List[Dict[str, Any]], ctx: "kitchen_plan.Context") -> List[str]:
    """Check an AI plan against the ingredient catalogue and the person's kitchen. Returns what is wrong (empty when fine).

    Every meal must name its ingredients; each must be a known ingredient within the person's diet and exclusions, and the
    ones not in the kitchen (and not pantry basics) may be at most MAX_EXTRAS different items over the week."""
    problems: List[str] = []
    extras: set = set()
    for day in days:
        for meal in day.get("meals", []):
            names = meal.get("ingredients")
            if not isinstance(names, list):
                problems.append(f"{meal.get('name')}: no ingredient list")
                continue
            for name in names:
                item = kitchen.catalogue.find(name)
                if item is None:
                    problems.append(f"{meal.get('name')}: unknown ingredient {name}")
                elif item.id not in ctx.allowed:
                    problems.append(f"{meal.get('name')}: {item.name} is outside the diet or food list")
                elif item.id not in ctx.available:
                    extras.add(item.id)
    if len(extras) > kitchen_plan.MAX_EXTRAS:
        problems.append(f"{len(extras)} extra ingredients (at most {kitchen_plan.MAX_EXTRAS})")
    return problems


def apply_kitchen_fields(candidate: Dict[str, Any], ctx: "kitchen_plan.Context") -> None:
    """Turn the model's ingredient names into catalogue ids, and mark what has to be bought."""
    for day in candidate["days"]:
        for meal in day["meals"]:
            ids = [item.id for item in (kitchen.catalogue.find(name) for name in meal["ingredients"]) if item is not None]
            ids = [iid for iid in dict.fromkeys(ids) if iid not in ctx.assumed]
            meal["ingredients"] = ids
            meal["extras"] = [iid for iid in ids if iid not in ctx.kitchen_ids]
    candidate.update({"kitchen_based": True, "kitchen_hash": ctx.signature, "also_buy": kitchen_plan.plan_extras(candidate["days"]), "generated_by": "groq kitchen engine"})


def kitchen_prompt_context(ctx: "kitchen_plan.Context") -> Dict[str, Any]:
    """What the plan prompt is told about the kitchen: names the model can copy exactly, and how many extras it may add."""
    by_id = kitchen.catalogue.by_id
    return {
        "kitchen_items": [by_id[iid].name for iid in ctx.order if iid in ctx.kitchen_ids],
        "extra_items_allowed": [by_id[iid].name for iid in sorted(ctx.allowed) if iid not in ctx.available and by_id[iid].group != "pantry"],
        "max_extra_items": kitchen_plan.MAX_EXTRAS,
        "cooked_meals": sorted(ctx.cooked),
        "cooking_time_cap_minutes": ctx.minutes_cap,
        "household_size": ctx.household,
    }


async def build_adaptive_plan(user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Regenerate the 7-day plan from the profile, the kitchen (when there is one) and the last week of logged behaviour."""
    week_ago = (local_today(user_zone(profile)) - timedelta(days=7)).isoformat()
    meals = await db.meals.find({"user_id": user_id, "date": {"$gte": week_ago}}, {"_id": 0}).to_list(200)
    activities = await db.activities.find({"user_id": user_id, "date": {"$gte": week_ago}}, {"_id": 0}).to_list(200)
    weights = await db.weights.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(10)
    kitchen_doc = await db.kitchens.find_one({"user_id": user_id}, {"_id": 0})
    ctx = kitchen_plan.make_context(profile, kitchen_doc)
    if ctx:
        fallback = kitchen_plan.build_week(ctx, profile, portion_for)
        fallback["updated_at"] = now_iso()  # plans are found, and Day 1 dated, by this
        system = KITCHEN_PLAN_SYSTEM
    else:
        fallback = local_plan(profile)
        fallback["reasoning"] = "Each day pairs familiar Indian foods with fibre, protein, healthy fats and hydration for steady energy."
        system = PLAN_SYSTEM
    context = plan_context(profile, meals, activities, weights)
    if ctx:
        context.update(kitchen_prompt_context(ctx))
    try:
        ai_text = await groq_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": f"Build this week's adaptive 7-day plan. Context: {json.dumps(context, default=str)}"}],
            user_id,
            max_tokens=9000,
        )
    except AIUnavailable as exc:
        if exc.code == "ai_busy":
            if ctx:
                # A kitchen plan never needs the AI: the kitchen engine answers instead, so the person is not left waiting.
                return fallback
            raise
        ai_text = ""
    if ai_text:
        match = re.search(r"\{.*\}", ai_text, re.DOTALL)
        if match:
            try:
                candidate = coerce_plan(json.loads(match.group(0)), fallback)
                if candidate.get("generated_by") == "groq adaptive engine":
                    violations = plan_restriction_violations(candidate["days"], profile)
                    if violations:
                        logger.warning("Groq plan for %s violated dietary restrictions (%s); using fallback", user_id, violations)
                        return fallback
                    if ctx:
                        problems = kitchen_plan_problems(candidate["days"], ctx)
                        if problems:
                            logger.warning("Groq plan for %s does not fit the kitchen (%s); using the kitchen engine", user_id, problems[:5])
                            return fallback
                        apply_kitchen_fields(candidate, ctx)
                    strip_condition_claims(candidate, profile, fallback)
                return candidate
            except json.JSONDecodeError:
                pass
    return fallback


def plan_start_date(plan: Dict[str, Any], zone: ZoneInfo = ZoneInfo("UTC")) -> Optional[date]:
    """The local calendar date the plan's Day 1 falls on."""
    try:
        started = datetime.fromisoformat(str(plan.get("updated_at")).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return started.astimezone(zone).date()


def plan_day_index(plan: Dict[str, Any], today: date, zone: ZoneInfo = ZoneInfo("UTC")) -> int:
    """Index of today's plan day: days since the plan started, wrapped within the plan length."""
    days = plan.get("days") or []
    start = plan_start_date(plan, zone)
    if not days or start is None:
        return 0
    return (today - start).days % len(days)


def logged_key(meal_type: Any, name: Any) -> tuple:
    return (str(meal_type or "").strip().lower(), str(name or "").strip().lower())


def ingredient_ref(iid: str, have: bool) -> Dict[str, Any]:
    item = kitchen.catalogue.by_id[iid]
    return {"id": iid, "name": item.name, "te": item.raw.get("te", ""), "group": item.group, "have": have}


def with_today_index(plan: Dict[str, Any], zone: ZoneInfo, todays_meals: List[Dict[str, Any]], kitchen_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Client view of a plan: today's day index, and today's plan meals flagged as logged.

    The flag is derived from today's meal log (not stored), so deleting a log entry un-flags the meal. A meal also says when
    something else was eaten in its slot ("ate_other"), what it uses (and whether the person has it), and the plan says what to
    buy and whether the kitchen changed since it was made."""
    clean = {key: value for key, value in plan.items() if key not in {"user_id", "_id"}}
    index = plan_day_index(plan, local_today(zone), zone)
    clean["today_index"] = index
    logged = {logged_key(item.get("meal_type"), item.get("name")) for item in todays_meals}
    slots_logged = {str(item.get("meal_type") or "").strip().lower() for item in todays_meals}
    have = set((kitchen_doc or {}).get("items") or [])
    kitchen_based = bool(plan.get("kitchen_based"))
    known = kitchen.catalogue.by_id
    days = []
    for position, day in enumerate(clean.get("days") or []):
        meals = []
        for meal in day.get("meals", []):
            is_logged = position == index and logged_key(meal.get("type"), meal.get("name")) in logged
            other = position == index and not is_logged and str(meal.get("type") or "").strip().lower() in slots_logged
            uses = [ingredient_ref(iid, iid in have or not kitchen_based) for iid in meal.get("ingredients") or [] if iid in known and not known[iid].assumed]
            meals.append({**meal, "logged": is_logged, "ate_other": other, "uses": uses})
        days.append({**day, "meals": meals})
    clean["days"] = days
    clean["kitchen_based"] = kitchen_based
    clean["also_buy"] = [ingredient_ref(iid, False) for iid in plan.get("also_buy") or [] if iid in known]
    clean["kitchen_changed"] = (plan.get("kitchen_hash") or None) != kitchen_plan.kitchen_signature(kitchen_doc)
    return clean


async def todays_meals(user_id: str, zone: ZoneInfo) -> List[Dict[str, Any]]:
    return await db.meals.find({"user_id": user_id, "date": local_today(zone).isoformat()}, {"_id": 0}).to_list(100)


PLANS_KEPT_PER_USER = 5


async def save_plan(plan: Dict[str, Any]) -> None:
    """Insert a new plan, then delete the user's older ones beyond the latest PLANS_KEPT_PER_USER.

    The plan just inserted is never deleted, even if its timestamp sorts oddly."""
    result = await db.plans.insert_one(plan)
    user_id = plan["user_id"]
    keep = await db.plans.find({"user_id": user_id}, {"_id": 1}).sort([("updated_at", DESCENDING), ("_id", DESCENDING)]).limit(PLANS_KEPT_PER_USER).to_list(PLANS_KEPT_PER_USER)
    keep_ids = [doc["_id"] for doc in keep]
    if result.inserted_id not in keep_ids:
        keep_ids = [result.inserted_id] + keep_ids[: PLANS_KEPT_PER_USER - 1]
    await db.plans.delete_many({"user_id": user_id, "_id": {"$nin": keep_ids}})


@api_router.get("/plan")
async def get_plan(user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    zone = user_zone(profile)
    kitchen_doc = await db.kitchens.find_one({"user_id": user["id"]}, {"_id": 0})
    existing = await db.plans.find_one({"user_id": user["id"]}, {"_id": 0}, sort=[("updated_at", -1)])
    if existing:
        start = plan_start_date(existing, zone)
        age_days = (local_today(zone) - start).days if start else 0
        if age_days < 7:
            return with_today_index(existing, zone, await todays_meals(user["id"], zone), kitchen_doc)
    # Missing or week-old plan → adaptive regeneration from recent logs
    try:
        plan = await build_adaptive_plan(user["id"], profile)
    except AIUnavailable as exc:
        # Rate limited: keep showing the old plan (or an unsaved fallback) and say so; the next visit retries.
        shown = existing or {**local_plan(profile), "reasoning": "A balanced starter plan while the AI is busy."}
        return {**with_today_index(shown, zone, await todays_meals(user["id"], zone), kitchen_doc), "ai_status": exc.code, "ai_message": exc.message}
    plan["user_id"] = user["id"]
    await save_plan(plan)
    return with_today_index(plan, zone, await todays_meals(user["id"], zone), kitchen_doc)


@api_router.post("/plan/regenerate")
async def regenerate_plan(user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    try:
        plan = await build_adaptive_plan(user["id"], profile)
    except AIUnavailable as exc:
        raise ai_error(exc) from exc
    plan["user_id"] = user["id"]
    await save_plan(plan)
    zone = user_zone(profile)
    kitchen_doc = await db.kitchens.find_one({"user_id": user["id"]}, {"_id": 0})
    return with_today_index(plan, zone, await todays_meals(user["id"], zone), kitchen_doc)


class SwapInput(BaseModel):
    day: int = Field(ge=0, le=6)
    type: str
    name: str = Field(min_length=1, max_length=120)


async def latest_plan_doc(user_id: str) -> Optional[Dict[str, Any]]:
    """The newest plan including its database id (the client view leaves the id out)."""
    return await db.plans.find_one({"user_id": user_id}, sort=[("updated_at", -1)])


def swap_context(profile: Dict[str, Any], kitchen_doc: Optional[Dict[str, Any]]) -> "kitchen_plan.Context":
    """Swaps and adjustments always work: without a kitchen they draw on what a typical home has."""
    return kitchen_plan.make_context(profile, kitchen_doc, default_kitchen=True)


def check_swap_target(plan: Optional[Dict[str, Any]], day: int, slot: str) -> Dict[str, Any]:
    if slot not in kitchen_plan.SLOT_ORDER:
        raise HTTPException(status_code=422, detail="Unknown meal type")
    if not plan:
        raise HTTPException(status_code=404, detail="No plan yet")
    days = plan.get("days") or []
    if day >= len(days):
        raise HTTPException(status_code=422, detail="Unknown day")
    meal = next((m for m in days[day].get("meals", []) if m.get("type") == slot), None)
    if not meal:
        raise HTTPException(status_code=404, detail="That meal is not in the plan")
    return meal


@api_router.get("/plan/swap")
async def swap_options(day: int = Query(ge=0, le=6), type: str = "", user: Dict[str, Any] = Depends(current_user)):
    """Three other meals for one slot of the plan, from the same kitchen."""
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    plan = await latest_plan_doc(user["id"])
    check_swap_target(plan, day, type)
    kitchen_doc = await db.kitchens.find_one({"user_id": user["id"]}, {"_id": 0})
    options = kitchen_plan.alternatives(swap_context(profile, kitchen_doc), profile, portion_for, plan, day, type)
    view = with_today_index({**plan, "days": [{**d, "meals": options if i == day else []} for i, d in enumerate(plan["days"])]}, user_zone(profile), [], kitchen_doc)
    return {"alternatives": view["days"][day]["meals"]}


@api_router.post("/plan/swap")
async def swap_meal(payload: SwapInput, user: Dict[str, Any] = Depends(current_user)):
    """Replace one planned meal by one of the offered alternatives (chosen by name, so only real options can be put in)."""
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    zone = user_zone(profile)
    plan = await latest_plan_doc(user["id"])
    current = check_swap_target(plan, payload.day, payload.type)
    todays = await todays_meals(user["id"], zone)
    if payload.day == plan_day_index(plan, local_today(zone), zone) and logged_key(current.get("type"), current.get("name")) in {logged_key(m.get("meal_type"), m.get("name")) for m in todays}:
        raise HTTPException(status_code=409, detail="This meal is already logged")
    kitchen_doc = await db.kitchens.find_one({"user_id": user["id"]}, {"_id": 0})
    options = kitchen_plan.alternatives(swap_context(profile, kitchen_doc), profile, portion_for, plan, payload.day, payload.type, count=12)
    chosen = next((meal for meal in options if meal["name"] == payload.name), None)
    if not chosen:
        raise HTTPException(status_code=422, detail="That meal is not one of the options")
    days = plan["days"]
    days[payload.day]["meals"] = [chosen if m.get("type") == payload.type else m for m in days[payload.day]["meals"]]
    changes: Dict[str, Any] = {"days": days}
    if plan.get("kitchen_based"):
        changes["also_buy"] = kitchen_plan.plan_extras(days)
    await db.plans.update_one({"_id": plan["_id"]}, {"$set": changes})
    return with_today_index({**plan, **changes}, zone, todays, kitchen_doc)


def protein_target(profile: Dict[str, Any]) -> int:
    """Daily protein the plan's own meals add up to: the protein share of the calorie target (see portion_for)."""
    share = 0.25 if profile.get("wellness_goal", "Healthier living") in {"Muscle building", "Weight gain", "Weight loss"} else 0.20
    return round(calorie_target(profile) * share / 4)


CHECKIN_LOW_PROTEIN = 0.75
CHECKIN_LOW_ENERGY = 0.6
CHECKIN_ABOVE = 1.25


async def checkin_result(user_id: str, profile: Dict[str, Any], plan: Optional[Dict[str, Any]], zone: ZoneInfo) -> Dict[str, Any]:
    today = local_today(zone)
    meals = await todays_meals(user_id, zone)
    calories = sum(int(m.get("calories") or 0) for m in meals)
    protein = round(sum(float(m.get("protein_g") or 0) for m in meals))
    target_calories, target_protein = calorie_target(profile), protein_target(profile)
    if not meals:
        status_code = "nothing_logged"
    elif protein < target_protein * CHECKIN_LOW_PROTEIN:
        status_code = "low_protein"
    elif calories < target_calories * CHECKIN_LOW_ENERGY:
        status_code = "low_energy"
    elif calories > target_calories * CHECKIN_ABOVE:
        status_code = "above"
    else:
        status_code = "on_track"
    return {"date": today.isoformat(), "status": status_code, "calories": calories, "target_calories": target_calories, "protein_g": protein, "target_protein_g": target_protein, "adjusted_day": None}


@api_router.get("/checkin")
async def get_checkin(user: Dict[str, Any] = Depends(current_user)):
    """Today's evening check-in if it was done."""
    profile, zone, today = await user_clock(user["id"])
    plan = await latest_plan_doc(user["id"])
    done = (plan or {}).get("checkin")
    return {"done": bool(done and done.get("date") == today.isoformat()), "result": done if done and done.get("date") == today.isoformat() else None}


@api_router.post("/checkin")
async def post_checkin(user: Dict[str, Any] = Depends(current_user)):
    """Look at today's logged food against the plan's own numbers. If protein ran low, tomorrow's meals are made again to lean on
    protein-rich foods from the person's kitchen. Honest and simple: nothing else changes, and nothing here is medical advice."""
    profile, zone, today = await user_clock(user["id"])
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    plan = await latest_plan_doc(user["id"])
    if not plan:
        raise HTTPException(status_code=404, detail="No plan yet")
    earlier = plan.get("checkin")
    if earlier and earlier.get("date") == today.isoformat() and earlier.get("status") != "nothing_logged":
        return {"done": True, "result": earlier, "repeat": True}
    result = await checkin_result(user["id"], profile, plan, zone)
    if result["status"] == "low_protein":
        days = plan["days"]
        tomorrow = (plan_day_index(plan, today, zone) + 1) % len(days)
        kitchen_doc = await db.kitchens.find_one({"user_id": user["id"]}, {"_id": 0})
        days[tomorrow] = kitchen_plan.rebuild_day(swap_context(profile, kitchen_doc), profile, portion_for, plan, tomorrow, prefer_protein=True)
        result["adjusted_day"] = tomorrow
        changes: Dict[str, Any] = {"days": days, "checkin": result}
        if plan.get("kitchen_based"):
            changes["also_buy"] = kitchen_plan.plan_extras(days)
    else:
        changes = {"checkin": result}
    await db.plans.update_one({"_id": plan["_id"]}, {"$set": changes})
    return {"done": True, "result": result, "repeat": False}


@api_router.get("/plan/shopping-list")
async def shopping_list(user: Dict[str, Any] = Depends(current_user)):
    """The week's ingredients minus what the person already has at home, grouped for the shop."""
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    plan = await db.plans.find_one({"user_id": user["id"]}, {"_id": 0}, sort=[("updated_at", -1)])
    kitchen_doc = await db.kitchens.find_one({"user_id": user["id"]}, {"_id": 0})
    household = int((kitchen_doc or {}).get("household_size") or 2)
    if not plan or not plan.get("kitchen_based"):
        return {"kitchen_based": False, "household_size": household, "to_buy": [], "have": [], "kitchen_changed": bool(kitchen_doc and kitchen_doc.get("items"))}
    uses: Dict[str, int] = {}
    for day in plan.get("days", []):
        for meal in day.get("meals", []):
            for iid in meal.get("ingredients") or []:
                if iid in kitchen.catalogue.by_id and not kitchen.catalogue.by_id[iid].assumed:
                    uses[iid] = uses.get(iid, 0) + 1
    owned = set((kitchen_doc or {}).get("items") or [])
    order = {group: position for position, group in enumerate(kitchen.GROUPS)}

    def rows(ids: List[str]) -> List[Dict[str, Any]]:
        ordered = sorted(ids, key=lambda iid: (order.get(kitchen.catalogue.by_id[iid].group, 99), -uses[iid], kitchen.catalogue.by_id[iid].name))
        return [{**ingredient_ref(iid, iid in owned), "meals": uses[iid]} for iid in ordered]

    return {
        "kitchen_based": True,
        "household_size": household,
        "to_buy": rows([iid for iid in uses if iid not in owned]),
        "have": rows([iid for iid in uses if iid in owned]),
        "kitchen_changed": (plan.get("kitchen_hash") or None) != kitchen_plan.kitchen_signature(kitchen_doc),
    }


@api_router.get("/dashboard")
async def dashboard(user: Dict[str, Any] = Depends(current_user)):
    profile, _, local_date = await user_clock(user["id"])
    today = local_date.isoformat()
    meals = await db.meals.find({"user_id": user["id"], "date": today}, {"_id": 0}).to_list(50)
    activities = await db.activities.find({"user_id": user["id"], "date": today}, {"_id": 0}).to_list(50)
    calories = sum(int(item.get("calories") or 0) for item in meals)
    active = sum(int(item.get("active_calories") or 0) for item in activities)
    # Plain counts of what was logged today against the estimated target; no made-up score.
    return {
        "date": today,
        "meals": meals,
        "activities": activities,
        "calories": calories,
        "target_calories": calorie_target(profile or {}),
        "active_calories": active,
        "activity_minutes": sum(int(item.get("duration_min") or 0) for item in activities),
        "goal": (profile or {}).get("wellness_goal", "Healthier living"),
    }


@api_router.post("/meals")
async def log_meal(payload: MealLogInput, user: Dict[str, Any] = Depends(current_user)):
    _, _, today = await user_clock(user["id"])
    if payload.source == "plan":
        # A plan meal is logged once per day; repeated taps on "+" must not double-count it.
        existing = await db.meals.find({"user_id": user["id"], "date": today.isoformat(), "meal_type": payload.meal_type}, {"_id": 0}).to_list(50)
        if any(logged_key(item.get("meal_type"), item.get("name")) == logged_key(payload.meal_type, payload.name) for item in existing):
            raise HTTPException(status_code=409, detail="This meal is already logged today")
    meal = {**payload.model_dump(exclude_none=True), "id": str(uuid.uuid4()), "user_id": user["id"], "date": today.isoformat(), "created_at": now_iso()}
    response = dict(meal)
    await db.meals.insert_one(meal)
    return response


@api_router.patch("/meals/{meal_id}")
async def update_meal(meal_id: str, payload: MealPatchInput, user: Dict[str, Any] = Depends(current_user)):
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Nothing to update")
    changes["updated_at"] = now_iso()
    updated = await db.meals.find_one_and_update({"id": meal_id, "user_id": user["id"]}, {"$set": changes}, projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not updated:
        raise HTTPException(status_code=404, detail="Meal not found")
    return updated


async def delete_owned(collection: Any, entry_id: str, user_id: str, label: str) -> Dict[str, Any]:
    """Delete one log entry, only if it belongs to the signed-in user."""
    result = await collection.delete_one({"id": entry_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return {"deleted": True, "id": entry_id}


@api_router.delete("/meals/{meal_id}")
async def delete_meal(meal_id: str, user: Dict[str, Any] = Depends(current_user)):
    return await delete_owned(db.meals, meal_id, user["id"], "Meal")


def check_foods_rate_limit(user_id: str) -> None:
    wait = foods_limiter.record(f"foods:{user_id}")
    if wait:
        raise HTTPException(status_code=429, detail="Too many searches. Please wait a moment and try again.", headers={"Retry-After": str(wait)})


async def recent_meal_docs(user_id: str, limit: int) -> List[Dict[str, Any]]:
    """The person's most recently logged meals, one per distinct food name, newest first."""
    docs = await db.meals.find({"user_id": user_id}, {"_id": 0}).sort("created_at", DESCENDING).limit(200).to_list(200)
    seen, distinct = set(), []
    for doc in docs:
        key = foods.normalize(str(doc.get("name") or ""))
        if key and key not in seen:
            seen.add(key)
            distinct.append(doc)
        if len(distinct) >= limit:
            break
    return distinct


def food_from_meal(doc: Dict[str, Any], recent: bool = True) -> Dict[str, Any]:
    """A logged meal as a food row: the catalogue entry when the name matches one, else what the person logged."""
    known = foods.catalogue.find_by_name(str(doc.get("name") or ""))
    if known:
        return known.public(recent=recent)
    serving = doc.get("portion") or "1 serving (as logged)"
    return {
        "id": "meal-" + hashlib.sha1(foods.normalize(str(doc.get("name") or "")).encode()).hexdigest()[:12],
        "name": doc.get("name", ""),
        "te": "",
        "category": "Logged",
        "serving": serving,
        "calories": int(doc.get("calories") or 0),
        "protein_g": float(doc.get("protein_g") or 0),
        "carbs_g": float(doc.get("carbs_g") or 0),
        "fat_g": float(doc.get("fat_g") or 0),
        "servings": [{"label": serving, "factor": 1.0}],
        "estimate": False,
        "recent": recent,
    }


@api_router.get("/foods/search")
async def search_foods(q: str = "", limit: int = Query(20, ge=1, le=50), user: Dict[str, Any] = Depends(current_user)):
    """Suggestions while typing. An empty query returns the person's recent foods (or common ones if they have none)."""
    check_foods_rate_limit(user["id"])
    text = q.strip()[:80]
    recents = await recent_meal_docs(user["id"], 30)
    if not foods.normalize(text):
        if recents:
            return {"query": text, "kind": "recent", "results": [food_from_meal(doc) for doc in recents[:limit]]}
        return {"query": text, "kind": "popular", "results": [food.public() for food in foods.catalogue.popular(limit)]}
    return {"query": text, "kind": "search", "note": foods.catalogue.note, "results": foods.catalogue.search(text, limit, [doc["name"] for doc in recents])}


@api_router.get("/foods/recent")
async def recent_foods(limit: int = Query(10, ge=1, le=30), user: Dict[str, Any] = Depends(current_user)):
    check_foods_rate_limit(user["id"])
    return {"results": [food_from_meal(doc) for doc in await recent_meal_docs(user["id"], limit)]}


@api_router.get("/foods/frequent")
async def frequent_foods(limit: int = Query(10, ge=1, le=30), user: Dict[str, Any] = Depends(current_user)):
    """Foods logged at least twice in the last 90 days, most often first."""
    check_foods_rate_limit(user["id"])
    _, _, today = await user_clock(user["id"])
    pipeline = [
        {"$match": {"user_id": user["id"], "date": {"$gte": (today - timedelta(days=90)).isoformat()}}},
        {"$group": {"_id": {"$toLower": "$name"}, "count": {"$sum": 1}, "last": {"$max": "$created_at"}, "doc": {"$first": "$$ROOT"}}},
        {"$match": {"count": {"$gte": 2}}},
        {"$sort": {"count": -1, "last": -1}},
        {"$limit": limit},
    ]
    rows = await db.meals.aggregate(pipeline).to_list(limit)
    return {"results": [{**food_from_meal(row["doc"], recent=False), "times": row["count"]} for row in rows]}


# Compendium of Physical Activities MET values for the quick-log activities.
ACTIVITY_METS = {"walking": 3.5, "home strength": 5.0, "strength": 5.0, "yoga": 2.5, "cycling": 6.0, "running": 8.0}
DEFAULT_MET = 4.0
WALKING_KMH = 4.8


def estimate_active_calories(activity_type: str, duration_min: int, weight_kg: float) -> int:
    """kcal = MET x 3.5 x body weight (kg) / 200, per minute."""
    met = ACTIVITY_METS.get(activity_type.strip().lower(), DEFAULT_MET)
    return int(round(met * 3.5 * weight_kg / 200 * duration_min))


async def current_weight_kg(user_id: str, profile: Optional[Dict[str, Any]]) -> float:
    """Latest logged weight, else the profile weight, else 70 kg."""
    latest = await db.weights.find_one({"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)])
    return float((latest or {}).get("weight_kg") or (profile or {}).get("weight_kg") or 70)


@api_router.post("/activities")
async def log_activity(payload: ActivityInput, user: Dict[str, Any] = Depends(current_user)):
    profile, _, today = await user_clock(user["id"])
    activity = {**payload.model_dump(), "id": str(uuid.uuid4()), "user_id": user["id"], "date": today.isoformat(), "created_at": now_iso()}
    if payload.active_calories is None:
        activity["active_calories"] = estimate_active_calories(payload.activity_type, payload.duration_min, await current_weight_kg(user["id"], profile))
        if payload.activity_type.strip().lower() == "walking" and not payload.distance_km:
            activity["distance_km"] = round(payload.duration_min * WALKING_KMH / 60, 1)
    response = dict(activity)
    await db.activities.insert_one(activity)
    return response


@api_router.delete("/activities/{activity_id}")
async def delete_activity(activity_id: str, user: Dict[str, Any] = Depends(current_user)):
    return await delete_owned(db.activities, activity_id, user["id"], "Activity")


@api_router.post("/weight")
async def log_weight(payload: WeightInput, user: Dict[str, Any] = Depends(current_user)):
    _, _, today = await user_clock(user["id"])
    entry = {"id": str(uuid.uuid4()), "user_id": user["id"], "weight_kg": payload.weight_kg, "date": today.isoformat(), "created_at": now_iso()}
    response = dict(entry)
    await db.weights.insert_one(entry)
    return response


@api_router.delete("/weight/{entry_id}")
async def delete_weight(entry_id: str, user: Dict[str, Any] = Depends(current_user)):
    return await delete_owned(db.weights, entry_id, user["id"], "Weight entry")


@api_router.get("/progress")
async def progress(user: Dict[str, Any] = Depends(current_user)):
    entries = await db.weights.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    activities = await db.activities.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"weights": entries, "activities": activities, "review": "Small consistent choices compound. Review your energy, movement and meals together—not just the scale."}


COACH_SYSTEM = (
    "You are Wellstride, a warm bilingual Indian wellness coach. Give practical, non-diagnostic advice and keep answers under 140 words. "
    "Mention a doctor or dietitian for medical concerns. Use the conversation history for continuity but never invent health data. "
    "When the user asks for a recipe or a dish idea they could cook, end your reply with a fenced block exactly like "
    '```recipe\n{"name": str, "time_min": int, "calories": int, "protein_g": number, "carbs_g": number, "fat_g": number, '
    '"ingredients": [str], "steps": [str]}\n``` '
    "using realistic Indian home-cooking values. Include the block only for actual recipes. "
    "You give general wellness guidance, not medical advice: never diagnose, never suggest medicines, doses or stopping treatment, and do not claim "
    "your suggestions are medically tailored. If the user lists health conditions, keep suggestions generally sensible for them and remind them "
    "to confirm anything important with their doctor or dietitian. Never say a food or plan supports, manages, treats, helps or is good for a "
    "condition; describe only the food itself (for example 'lower in sugar, high in fibre')."
)


def coach_system_prompt(profile: Dict[str, Any], language: str) -> str:
    language_line = "Respond in Telugu." if language == "te" else "Respond in English."
    conditions = health_conditions(profile)
    conditions_line = f"Self-reported health conditions (user-provided, unverified): {', '.join(conditions)}." if conditions else "The user has not listed any health conditions."
    return f"{COACH_SYSTEM} {language_line} {conditions_line} User wellness profile (user-provided): {json.dumps(profile)}"

RECIPE_BLOCK = re.compile(r"```recipe\s*(\{.*?\})\s*```", re.DOTALL)


async def recent_coach_messages(user_id: str, limit: int) -> List[Dict[str, Any]]:
    """The user's latest `limit` coach messages, oldest first. (Sorting ascending with a cap returned the
    oldest messages, so a long conversation stopped showing, and stopped sending, anything recent.)"""
    latest = await db.coach_messages.find({"user_id": user_id}, {"_id": 0}).sort("created_at", DESCENDING).limit(limit).to_list(limit)
    return list(reversed(latest))


@api_router.get("/coach/history")
async def coach_history(user: Dict[str, Any] = Depends(current_user)):
    """Return stored conversation only when the user has coach memory enabled."""
    prefs = await db.permissions.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    if prefs and prefs.get("coach_memory") is False:
        return {"messages": [], "memory": False}
    return {"messages": await recent_coach_messages(user["id"], 30), "memory": True}


@api_router.post("/coach")
async def coach(payload: CoachInput, user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    prefs = await db.permissions.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    memory = prefs.get("coach_memory") is not False
    history: List[Dict[str, Any]] = []
    if memory:
        history = await recent_coach_messages(user["id"], 12)
    messages = [{"role": "system", "content": coach_system_prompt(profile, payload.language)}]
    for item in history[-12:]:
        messages.append({"role": "user" if item.get("role") == "user" else "assistant", "content": str(item.get("text", ""))[:600]})
    messages.append({"role": "user", "content": payload.message})
    try:
        response = await groq_chat(messages, user["id"])
    except AIUnavailable as exc:
        raise ai_error(exc) from exc
    if not response:
        # No provider configured (or an empty answer): say so rather than inventing a canned reply.
        raise ai_error(AIUnavailable("ai_unavailable", AI_UNAVAILABLE_MESSAGE))
    reply = response
    recipe: Optional[Dict[str, Any]] = None
    match = RECIPE_BLOCK.search(reply)
    if match:
        try:
            candidate = json.loads(match.group(1))
            recipe = {
                "name": str(candidate.get("name") or "Wellstride recipe")[:80],
                "time_min": max(1, min(180, int(candidate.get("time_min") or 20))),
                "calories": max(0, min(2000, int(candidate.get("calories") or 350))),
                "protein_g": max(0, min(200, float(candidate.get("protein_g") or 15))),
                "carbs_g": max(0, min(400, float(candidate.get("carbs_g") or 40))),
                "fat_g": max(0, min(250, float(candidate.get("fat_g") or 12))),
                "ingredients": [str(item)[:80] for item in (candidate.get("ingredients") or [])][:12],
                "steps": [str(step)[:200] for step in (candidate.get("steps") or [])][:10],
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            recipe = None
        reply = RECIPE_BLOCK.sub("", reply).strip()
    if memory:
        await db.coach_messages.insert_many([
            {"id": str(uuid.uuid4()), "user_id": user["id"], "role": "user", "text": payload.message, "created_at": now_iso()},
            {"id": str(uuid.uuid4()), "user_id": user["id"], "role": "coach", "text": reply, "recipe": recipe, "created_at": now_iso()},
        ])
    return {"reply": reply, "recipe": recipe, "memory": memory, "source": "groq"}


@api_router.get("/ingredients")
async def ingredients(q: str = ""):
    catalogue = [
        {"name": "Paneer", "category": "Protein", "tags": ["Indian", "vegetarian"]},
        {"name": "Tofu", "category": "Protein", "tags": ["global", "vegan"]},
        {"name": "Moong dal", "category": "Legume", "tags": ["Indian", "fibre"]},
        {"name": "Oats", "category": "Whole grain", "tags": ["global", "fibre"]},
        {"name": "Avocado", "category": "Healthy fat", "tags": ["global"]},
        {"name": "Chia seeds", "category": "Seeds", "tags": ["global", "fibre"]},
        {"name": "Pumpkin seeds", "category": "Seeds", "tags": ["global", "protein"]},
        {"name": "Almonds", "category": "Nuts", "tags": ["global", "healthy fat"]},
        {"name": "Rajma", "category": "Legume", "tags": ["Indian", "fibre"]},
        {"name": "Spinach", "category": "Vegetable", "tags": ["Indian", "micronutrients"]},
    ]
    query = q.strip().lower()
    return [item for item in catalogue if not query or query in item["name"].lower() or query in item["category"].lower()]


@api_router.get("/permissions")
async def permissions(user: Dict[str, Any] = Depends(current_user)):
    prefs = await db.permissions.find_one({"user_id": user["id"]}, {"_id": 0})
    return prefs or {"user_id": user["id"], "health_sync": False, "wearables": False, "analytics": False, "coach_memory": True}


@api_router.post("/permissions")
async def set_permissions(payload: Dict[str, bool], user: Dict[str, Any] = Depends(current_user)):
    clean = {key: bool(value) for key, value in payload.items() if key in {"health_sync", "wearables", "analytics", "coach_memory"}}
    clean.update({"user_id": user["id"], "updated_at": now_iso()})
    await db.permissions.update_one({"user_id": user["id"]}, {"$set": clean}, upsert=True)
    return clean


class VisionInput(BaseModel):
    image_base64: str = Field(min_length=200, max_length=9_000_000)
    language: str = "en"
    meal_type: str = "snack"


class ReminderPrefs(BaseModel):
    meals: bool = True
    hydration: bool = False
    movement: bool = False
    weekly: bool = True


class HealthRecordInput(BaseModel):
    external_id: str = Field(min_length=1, max_length=200)
    metric: str = Field(min_length=1, max_length=40)
    start: str = Field(default="", max_length=40)
    end: str = Field(default="", max_length=40)
    value: Optional[float] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    source: Optional[str] = None


def to_number(value: Any, default: float) -> float:
    """A model-supplied number, falling back to the default when it is missing or not numeric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@api_router.post("/coach/vision")
async def coach_vision(payload: VisionInput, user: Dict[str, Any] = Depends(current_user)):
    """Identify food from a base64 photo and estimate nutrition (user confirms)."""
    try:
        result = await vision.analyze_image(payload.image_base64, user["id"])
    except vision.VisionNotConfigured as exc:
        raise HTTPException(status_code=503, detail={"code": "vision_not_configured", "message": "Photo recognition isn't set up on this server yet. You can still log your meal by hand."}) from exc
    except vision.VisionUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "vision_unavailable", "message": "Photo recognition couldn't read this photo right now. Try again, or log your meal by hand."}) from exc
    parsed = result.data
    return {
        "name": str(parsed.get("name") or "Mixed home meal")[:80],
        "portion": str(parsed.get("portion") or "1 serving")[:60],
        "calories": max(0, min(3000, int(to_number(parsed.get("calories"), 350)))),
        "protein_g": max(0, min(300, to_number(parsed.get("protein_g"), 12))),
        "carbs_g": max(0, min(400, to_number(parsed.get("carbs_g"), 40))),
        "fat_g": max(0, min(250, to_number(parsed.get("fat_g"), 14))),
        "confidence": parsed.get("confidence") if parsed.get("confidence") in {"low", "medium", "high"} else "medium",
        "alternatives": [str(item)[:60] for item in (parsed.get("alternatives") or [])][:3],
        "meal_type": payload.meal_type,
        "model": result.model,
        "provider": result.provider,
    }


@api_router.get("/eat-now")
async def eat_now(user: Dict[str, Any] = Depends(current_user)):
    """What Should I Eat Now — based on today's intake, goal and plan."""
    stored_profile, zone, local_date = await user_clock(user["id"])
    profile = stored_profile or {}
    today = local_date.isoformat()
    meals = await db.meals.find({"user_id": user["id"], "date": today}, {"_id": 0}).to_list(50)
    plan = await db.plans.find_one({"user_id": user["id"]}, {"_id": 0}, sort=[("updated_at", -1)])
    target = calorie_target(profile)
    consumed = sum(int(item.get("calories", 0)) for item in meals)
    remaining = max(0, target - consumed)
    logged_types = {item.get("meal_type") for item in meals}
    suggestion: Optional[Dict[str, Any]] = None
    if plan and plan.get("days"):
        for meal in plan["days"][plan_day_index(plan, local_date, zone)].get("meals", []):
            if meal.get("type") not in logged_types:
                suggestion = meal
                break
    if not suggestion:
        suggestion = {"type": "snack", "name": "Buttermilk with roasted chana & fruit", "portion": "1 glass + 1 small bowl", "calories": 220, "protein_g": 12, "carbs_g": 30, "fat_g": 6}
    return {
        "suggestion": suggestion,
        "target_calories": target,
        "consumed_calories": consumed,
        "remaining_calories": remaining,
        "reasoning": "Based on what you have logged today, this keeps protein and fibre steady without overshooting your energy needs.",
        "disclaimer": "Estimates only — adjust portions to your hunger and your clinician's advice.",
    }


@api_router.get("/reminders")
async def get_reminders(user: Dict[str, Any] = Depends(current_user)):
    prefs = await db.reminders.find_one({"user_id": user["id"]}, {"_id": 0})
    return prefs or {"user_id": user["id"], **ReminderPrefs().model_dump()}


@api_router.put("/reminders")
async def put_reminders(payload: ReminderPrefs, user: Dict[str, Any] = Depends(current_user)):
    doc = {**payload.model_dump(), "user_id": user["id"], "updated_at": now_iso()}
    await db.reminders.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    return {key: value for key, value in doc.items() if key != "_id"}


@api_router.post("/health/sync")
async def health_sync(payload: List[HealthRecordInput], user: Dict[str, Any] = Depends(current_user)):
    """Idempotent ingestion of normalized HealthKit / Health Connect records.

    Privacy-first: records are accepted only after the user explicitly enables
    health sync in Settings."""
    prefs = await db.permissions.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    if not prefs.get("health_sync"):
        raise HTTPException(status_code=403, detail="Enable Health sync in privacy settings before syncing device data")
    if len(payload) > 1000:
        raise HTTPException(status_code=413, detail="Batch too large")
    upserted = 0
    for record in payload:
        doc = {**record.model_dump(), "user_id": user["id"], "received_at": now_iso()}
        result = await db.health_records.update_one(
            {"user_id": user["id"], "external_id": record.external_id, "source": record.source},
            {"$set": doc},
            upsert=True,
        )
        upserted += int(result.upserted_id is not None)
    return {"received": len(payload), "upserted": upserted}


@api_router.get("/health/summary")
async def health_summary(user: Dict[str, Any] = Depends(current_user)):
    """Today's device-measured activity (HealthKit / Health Connect), clearly sourced."""
    prefs = await db.permissions.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    _, zone, local_date = await user_clock(user["id"])
    # Records carry UTC ISO timestamps; compare against the user's local midnight expressed in UTC.
    day_start = datetime.combine(local_date, datetime.min.time(), tzinfo=zone).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    records = await db.health_records.find({"user_id": user["id"], "start": {"$gte": day_start}}, {"_id": 0}).to_list(500)
    steps = 0
    active = 0.0
    sleep_minutes = 0
    for record in records:
        metric = record.get("metric")
        if metric == "steps":
            steps += int(record.get("value") or 0)
        elif metric == "activeCalories":
            active += float(record.get("value") or 0)
        elif metric == "sleep":
            try:
                start = datetime.fromisoformat(str(record.get("start")).replace("Z", "+00:00"))
                end = datetime.fromisoformat(str(record.get("end")).replace("Z", "+00:00"))
                sleep_minutes += max(0, int((end - start).total_seconds() // 60))
            except (ValueError, TypeError):
                continue
    return {"connected": bool(prefs.get("health_sync")), "steps": steps, "sleep_minutes": sleep_minutes, "active_calories": int(active), "source": "device", "records": len(records)}


app.include_router(api_router)


# Public pages (no login). The app links to them, and Google Play asks for the privacy policy and account-deletion URLs.
def legal_page(page: str) -> HTMLResponse:
    return HTMLResponse(legal.render(page), headers={"Cache-Control": "public, max-age=300"})


@app.get("/privacy", include_in_schema=False)
async def privacy_page():
    return legal_page("privacy")


@app.get("/terms", include_in_schema=False)
async def terms_page():
    return legal_page("terms")


@app.get("/delete-account", include_in_schema=False)
async def delete_account_page():
    return legal_page("delete-account")
# Auth uses Bearer tokens, not cookies, so credentials (cookies) are not allowed cross-origin.
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_origin_regex=None if CORS_ORIGINS else LOCAL_ORIGIN_PATTERN, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])