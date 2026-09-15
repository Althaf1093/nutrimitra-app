from datetime import datetime, timedelta, timezone
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import bcrypt
import httpx
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.getenv("DB_NAME", "nutrimitra")
JWT_SECRET = os.getenv("JWT_SECRET", "nutrimitra-local-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
app = FastAPI(title="NutriMitra API", version="1.0.0")
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)
logger = logging.getLogger("nutrimitra")


class AuthInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=80)


class TokenResponse(BaseModel):
    token: str
    user: Dict[str, Any]


class ProfileInput(BaseModel):
    age: int = Field(ge=13, le=100)
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


class MealLogInput(BaseModel):
    meal_type: str
    name: str
    calories: int = Field(ge=0, le=3000)
    protein_g: float = Field(ge=0, le=300)
    carbs_g: float = Field(ge=0, le=400)
    fat_g: float = Field(ge=0, le=250)
    source: str = "manual"


class ActivityInput(BaseModel):
    activity_type: str
    duration_min: int = Field(ge=1, le=1440)
    distance_km: float = Field(default=0, ge=0, le=500)
    active_calories: int = Field(default=0, ge=0, le=10000)
    source: str = "manual estimate"


class WeightInput(BaseModel):
    weight_kg: float = Field(gt=25, lt=300)


class CoachInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: str = "en"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": doc.get("id", ""),
        "email": doc.get("email", ""),
        "name": doc.get("name", ""),
        "language": doc.get("language", "en"),
        "onboarding_complete": bool(doc.get("onboarding_complete", False)),
    }


def issue_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue")
    user_id: Optional[str] = None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        session = await db.user_sessions.find_one({"session_token": credentials.credentials}, {"_id": 0})
        if session and str(session.get("expires_at", "")) > now_iso():
            user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return user


@api_router.get("/")
async def root():
    return {"name": "NutriMitra", "status": "ready", "ai_provider": "groq", "ai_model": GROQ_MODEL}


@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(payload: AuthInput):
    email = payload.email.lower()
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
    }
    await db.users.insert_one(user)
    return {"token": issue_token(user["id"]), "user": public_user(user)}


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(payload: AuthInput):
    user = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0})
    if not user or not bcrypt.checkpw(payload.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return {"token": issue_token(user["id"]), "user": public_user(user)}


class SessionInput(BaseModel):
    session_id: str = Field(min_length=6, max_length=300)


@api_router.post("/auth/session")
async def auth_session(payload: SessionInput):
    """Exchange a managed Google OAuth session_id for an app session token."""
    handoff = os.getenv("GOOGLE_AUTH_HANDOFF_URL", "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data")
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            response = await http.get(handoff, headers={"X-Session-ID": payload.session_id})
    except Exception as exc:
        logger.warning("Google session exchange failed: %s", exc)
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified")
    data = response.json()
    email = str(data.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": str(data.get("name") or email.split("@")[0]).title(),
            "picture": data.get("picture", ""),
            "password_hash": "",
            "language": "en",
            "onboarding_complete": False,
            "created_at": now_iso(),
        }
        await db.users.insert_one(user)
    session_token = data.get("session_token") or str(uuid.uuid4())
    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user["id"],
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": now_iso(),
    })
    return {"session_token": session_token, "user": public_user(user)}


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


def portion_for(profile: Dict[str, Any], meal: str) -> Dict[str, Any]:
    goal = profile.get("wellness_goal", "Healthier living")
    protein = 32 if goal in {"Muscle building", "Weight gain"} else 24
    portions = {"breakfast": "1 bowl", "lunch": "1 balanced plate", "snack": "1 small bowl", "dinner": "1 plate"}
    return {"portion": portions.get(meal, "1 serving"), "protein_g": protein, "carbs_g": 42, "fat_g": 16, "calories": 430}


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
            nutrition = portion_for(profile, meal_type)
            meals.append({"type": meal_type, "name": name, **nutrition, "logged": False})
        days.append({"day": index, "title": f"Day {index}", "focus": "Protein + fibre balance", "meals": meals})
    return {"goal": profile.get("wellness_goal", "Healthier living"), "days": days, "generated_by": "NutriMitra nutrition engine", "updated_at": now_iso()}


async def groq_chat(messages: List[Dict[str, str]], user_id: str, max_tokens: int = 1200) -> str:
    """Single swappable Groq chat call used by every AI surface."""
    if not GROQ_API_KEY:
        return ""
    body = {"model": GROQ_MODEL, "temperature": 0.4, "max_tokens": max_tokens, "messages": messages}
    try:
        async with httpx.AsyncClient(timeout=35) as http:
            response = await http.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=body)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Groq request failed for %s: %s", user_id, exc)
        return ""


async def groq_text(system: str, prompt: str, user_id: str) -> str:
    return await groq_chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}], user_id)


PLAN_SYSTEM = (
    "You are NutriMitra's Indian nutrition planning engine. Return ONLY valid JSON, no markdown: "
    '{"days": [{"day": 1, "title": str, "focus": str, "meals": [{"type": "breakfast"|"lunch"|"snack"|"dinner", "name": str, "portion": str, '
    '"calories": int, "protein_g": number, "carbs_g": number, "fat_g: number}]}, ...], "reasoning": str} — exactly 7 days, exactly 4 meals '
    "(breakfast, lunch, snack, dinner) per day. Rules: Indian-first meals with global nutritious ingredients where helpful; strictly respect "
    "dietary preferences, allergies and disliked foods; match cooking time and budget; balance protein, fibre and healthy fats; avoid repeating "
    "meals the user logged recently."
)


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
                    "logged": False,
                })
            except (TypeError, ValueError, AttributeError):
                return fallback
        cleaned.append({"day": index, "title": str(day.get("title") or f"Day {index}")[:40], "focus": str(day.get("focus") or "Balanced nutrition")[:80], "meals": safe_meals})
    return {"goal": fallback["goal"], "days": cleaned, "reasoning": str(candidate.get("reasoning") or fallback.get("reasoning", ""))[:600], "generated_by": "groq adaptive engine", "updated_at": now_iso()}


async def build_adaptive_plan(user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Regenerate the 7-day plan from the profile plus the last week of logged behaviour."""
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    meals = await db.meals.find({"user_id": user_id, "date": {"$gte": week_ago}}, {"_id": 0}).to_list(200)
    activities = await db.activities.find({"user_id": user_id, "date": {"$gte": week_ago}}, {"_id": 0}).to_list(200)
    weights = await db.weights.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(10)
    fallback = local_plan(profile)
    fallback["reasoning"] = "Each day pairs familiar Indian foods with fibre, protein, healthy fats and hydration for steady energy."
    context = {
        "profile": profile,
        "recent_meals_logged": [str(item.get("name", ""))[:40] for item in meals[-14:]],
        "activity_sessions_last_7_days": len(activities),
        "recent_weights_kg": [item.get("weight_kg") for item in weights[:7]],
    }
    ai_text = await groq_chat(
        [{"role": "system", "content": PLAN_SYSTEM}, {"role": "user", "content": f"Build this week's adaptive 7-day plan. Context: {json.dumps(context, default=str)}"}],
        user_id,
        max_tokens=9000,
    )
    if ai_text:
        match = re.search(r"\{.*\}", ai_text, re.DOTALL)
        if match:
            try:
                return coerce_plan(json.loads(match.group(0)), fallback)
            except json.JSONDecodeError:
                pass
    return fallback


@api_router.get("/plan")
async def get_plan(user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    existing = await db.plans.find_one({"user_id": user["id"]}, {"_id": 0}, sort=[("updated_at", -1)])
    if existing:
        try:
            age_days = (datetime.now(timezone.utc).date() - datetime.fromisoformat(str(existing.get("updated_at")).replace("Z", "+00:00")).date()).days
        except (ValueError, TypeError):
            age_days = 0
        if age_days < 7:
            return existing
    # Missing or week-old plan → adaptive regeneration from recent logs
    plan = await build_adaptive_plan(user["id"], profile)
    plan["user_id"] = user["id"]
    await db.plans.insert_one(plan)
    return {key: value for key, value in plan.items() if key not in {"user_id", "_id"}}


@api_router.post("/plan/regenerate")
async def regenerate_plan(user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    plan = await build_adaptive_plan(user["id"], profile)
    plan["user_id"] = user["id"]
    await db.plans.insert_one(plan)
    return {key: value for key, value in plan.items() if key not in {"user_id", "_id"}}


@api_router.get("/dashboard")
async def dashboard(user: Dict[str, Any] = Depends(current_user)):
    today = datetime.now(timezone.utc).date().isoformat()
    meals = await db.meals.find({"user_id": user["id"], "date": today}, {"_id": 0}).to_list(50)
    activities = await db.activities.find({"user_id": user["id"], "date": today}, {"_id": 0}).to_list(50)
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    calories = sum(item.get("calories", 0) for item in meals)
    active = sum(item.get("active_calories", 0) for item in activities)
    return {"date": today, "meals": meals, "activities": activities, "calories": calories, "active_calories": active, "readiness": min(96, 64 + len(activities) * 7 + len(meals) * 4), "goal": (profile or {}).get("wellness_goal", "Healthier living")}


@api_router.post("/meals")
async def log_meal(payload: MealLogInput, user: Dict[str, Any] = Depends(current_user)):
    meal = {**payload.model_dump(), "id": str(uuid.uuid4()), "user_id": user["id"], "date": datetime.now(timezone.utc).date().isoformat(), "created_at": now_iso()}
    response = dict(meal)
    await db.meals.insert_one(meal)
    return response


@api_router.post("/activities")
async def log_activity(payload: ActivityInput, user: Dict[str, Any] = Depends(current_user)):
    activity = {**payload.model_dump(), "id": str(uuid.uuid4()), "user_id": user["id"], "date": datetime.now(timezone.utc).date().isoformat(), "created_at": now_iso()}
    response = dict(activity)
    await db.activities.insert_one(activity)
    return response


@api_router.post("/weight")
async def log_weight(payload: WeightInput, user: Dict[str, Any] = Depends(current_user)):
    entry = {"id": str(uuid.uuid4()), "user_id": user["id"], "weight_kg": payload.weight_kg, "date": datetime.now(timezone.utc).date().isoformat(), "created_at": now_iso()}
    response = dict(entry)
    await db.weights.insert_one(entry)
    return response


@api_router.get("/progress")
async def progress(user: Dict[str, Any] = Depends(current_user)):
    entries = await db.weights.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    activities = await db.activities.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"weights": entries, "activities": activities, "review": "Small consistent choices compound. Review your energy, movement and meals together—not just the scale."}


COACH_SYSTEM = (
    "You are NutriMitra, a warm bilingual Indian wellness coach. Give practical, non-diagnostic advice and keep answers under 140 words. "
    "Mention a doctor or dietitian for medical concerns. Use the conversation history for continuity but never invent health data. "
    "When the user asks for a recipe or a dish idea they could cook, end your reply with a fenced block exactly like "
    '```recipe\n{"name": str, "time_min": int, "calories": int, "protein_g": number, "carbs_g": number, "fat_g": number, '
    '"ingredients": [str], "steps": [str]}\n``` '
    "using realistic Indian home-cooking values. Include the block only for actual recipes."
)

RECIPE_BLOCK = re.compile(r"```recipe\s*(\{.*?\})\s*```", re.DOTALL)


@api_router.get("/coach/history")
async def coach_history(user: Dict[str, Any] = Depends(current_user)):
    """Return stored conversation only when the user has coach memory enabled."""
    prefs = await db.permissions.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    if prefs and prefs.get("coach_memory") is False:
        return {"messages": [], "memory": False}
    messages = await db.coach_messages.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(60)
    return {"messages": messages[-30:], "memory": True}


@api_router.post("/coach")
async def coach(payload: CoachInput, user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    prefs = await db.permissions.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    memory = prefs.get("coach_memory") is not False
    history: List[Dict[str, Any]] = []
    if memory:
        history = await db.coach_messages.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(24)
    language_line = "Respond in Telugu." if payload.language == "te" else "Respond in English."
    messages = [{"role": "system", "content": f"{COACH_SYSTEM} {language_line} User wellness profile (user-provided): {json.dumps(profile)}"}]
    for item in history[-12:]:
        messages.append({"role": "user" if item.get("role") == "user" else "assistant", "content": str(item.get("text", ""))[:600]})
    messages.append({"role": "user", "content": payload.message})
    response = await groq_chat(messages, user["id"])
    reply = response or "I’m here with you. Try a balanced plate: half colourful vegetables, a quarter protein, and a quarter whole-grain carbohydrate. Tell me what ingredients you have and I’ll make it practical."
    recipe: Optional[Dict[str, Any]] = None
    match = RECIPE_BLOCK.search(reply)
    if match:
        try:
            candidate = json.loads(match.group(1))
            recipe = {
                "name": str(candidate.get("name") or "NutriMitra recipe")[:80],
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
    return {"reply": reply, "recipe": recipe, "memory": memory, "source": "groq" if response else "nutrition guidance"}


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


EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY", "")

VISION_PROMPT = (
    "Identify the food in this photo for an Indian wellness app. Respond with ONLY compact JSON, no markdown: "
    '{"name": str, "portion": str, "calories": int, "protein_g": number, "carbs_g": number, "fat_g": number, '
    '"confidence": "low|medium|high", "alternatives": [str, str]}. '
    "Estimate for a typical home serving. Prefer Indian dish names when relevant."
)


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


async def pick_vision_model() -> str:
    """Dynamically select an active Groq vision-capable model (never hardcoded). Empty string = none available."""
    if not GROQ_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            response = await http.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
            response.raise_for_status()
            ids = [str(model.get("id", "")) for model in response.json().get("data", [])]
    except Exception as exc:
        logger.warning("Groq model listing failed: %s", exc)
        return ""
    named = sorted(model for model in ids if "vision" in model.lower())
    if named:
        return named[0]
    llama4 = sorted(model for model in ids if "llama-4" in model.lower() and ("scout" in model.lower() or "maverick" in model.lower()))
    return llama4[0] if llama4 else ""


async def groq_vision(image_base64: str, user_id: str) -> tuple:
    """Groq-first vision path. Empty text means no usable Groq vision model."""
    model = await pick_vision_model()
    if not model:
        return "", ""
    body = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 500,
        "messages": [{"role": "user", "content": [{"type": "text", "text": VISION_PROMPT}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}]}],
    }
    try:
        async with httpx.AsyncClient(timeout=45) as http:
            response = await http.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=body)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"], model
    except Exception as exc:
        logger.warning("Groq vision failed for %s: %s", user_id, exc)
        return "", ""


async def emergent_vision(image_base64: str, user_id: str) -> str:
    """Fallback vision path via the Emergent universal key (OpenAI vision model)."""
    if not EMERGENT_LLM_KEY:
        return ""
    try:
        from emergentintegrations.llm.chat import ImageContent, LlmChat, UserMessage

        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"vision-{user_id}-{uuid.uuid4().hex[:8]}", system_message="You are a precise nutrition vision analyst.").with_model("openai", "gpt-5.4-mini")
        return str(await chat.send_message(UserMessage(text=VISION_PROMPT, file_contents=[ImageContent(image_base64=image_base64)])))
    except Exception as exc:
        logger.warning("Emergent vision fallback failed for %s: %s", user_id, exc)
        return ""


@api_router.post("/coach/vision")
async def coach_vision(payload: VisionInput, user: Dict[str, Any] = Depends(current_user)):
    """Identify food from a base64 photo and estimate nutrition (user confirms)."""
    text, model = await groq_vision(payload.image_base64, user["id"])
    if not text:
        text = await emergent_vision(payload.image_base64, user["id"])
        model = "openai/gpt-5.4-mini"
    if not text:
        raise HTTPException(status_code=502, detail="Photo recognition is unavailable right now — please log manually")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    parsed: Dict[str, Any] = {}
    if match:
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            parsed = {}
    if not parsed:
        raise HTTPException(status_code=502, detail="Could not read nutrition from this photo — try another or log manually")
    return {
        "name": str(parsed.get("name") or "Mixed home meal")[:80],
        "portion": str(parsed.get("portion") or "1 serving")[:60],
        "calories": max(0, min(3000, int(parsed.get("calories") or 350))),
        "protein_g": max(0, min(300, float(parsed.get("protein_g") or 12))),
        "carbs_g": max(0, min(400, float(parsed.get("carbs_g") or 40))),
        "fat_g": max(0, min(250, float(parsed.get("fat_g") or 14))),
        "confidence": parsed.get("confidence") if parsed.get("confidence") in {"low", "medium", "high"} else "medium",
        "alternatives": [str(item)[:60] for item in (parsed.get("alternatives") or [])][:3],
        "meal_type": payload.meal_type,
        "model": model,
    }


@api_router.get("/eat-now")
async def eat_now(user: Dict[str, Any] = Depends(current_user)):
    """What Should I Eat Now — based on today's intake, goal and plan."""
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    today = datetime.now(timezone.utc).date().isoformat()
    meals = await db.meals.find({"user_id": user["id"], "date": today}, {"_id": 0}).to_list(50)
    plan = await db.plans.find_one({"user_id": user["id"]}, {"_id": 0}, sort=[("updated_at", -1)])
    weight = float(profile.get("weight_kg") or 70)
    height = float(profile.get("height_cm") or 165)
    age = int(profile.get("age") or 30)
    sex_adjust = 5 if profile.get("sex") == "Male" else -161 if profile.get("sex") == "Female" else -78
    activity_factor = {"Lightly active": 1.4, "Moderately active": 1.55, "Very active": 1.7}.get(str(profile.get("activity_level", "")), 1.5)
    goal_adjust = {"Weight loss": -400, "Weight gain": 300, "Muscle building": 250}.get(str(profile.get("wellness_goal", "")), 0)
    target = max(1200, int(((10 * weight) + (6.25 * height) - (5 * age) + sex_adjust) * activity_factor + goal_adjust))
    consumed = sum(int(item.get("calories", 0)) for item in meals)
    remaining = max(0, target - consumed)
    logged_types = {item.get("meal_type") for item in meals}
    suggestion: Optional[Dict[str, Any]] = None
    for day in (plan or {}).get("days", [])[:1]:
        for meal in day.get("meals", []):
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
    today = datetime.now(timezone.utc).date().isoformat()
    records = await db.health_records.find({"user_id": user["id"], "start": {"$gte": today}}, {"_id": 0}).to_list(500)
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
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()