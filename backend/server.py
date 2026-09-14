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
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Session expired") from exc
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


@api_router.post("/auth/google", response_model=TokenResponse)
async def google_auth():
    raise HTTPException(status_code=501, detail="Google sign-in is ready for the managed OAuth handoff")


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


async def groq_text(system: str, prompt: str, user_id: str) -> str:
    if not GROQ_API_KEY:
        return ""
    body = {"model": GROQ_MODEL, "temperature": 0.4, "max_tokens": 1200, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    try:
        async with httpx.AsyncClient(timeout=35) as http:
            response = await http.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=body)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Groq request failed for %s: %s", user_id, exc)
        return ""


@api_router.get("/plan")
async def get_plan(user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=409, detail="Complete your wellness profile first")
    existing = await db.plans.find_one({"user_id": user["id"]}, {"_id": 0}, sort=[("updated_at", -1)])
    if existing:
        return existing
    plan = local_plan(profile)
    ai_text = await groq_text("You are NutriMitra, a careful Indian nutrition coach. Return concise, safe guidance without diagnoses.", f"Create one short reasoning note for this profile and goal: {json.dumps(profile)}", user["id"])
    plan["reasoning"] = ai_text.strip() or "Each day pairs familiar Indian foods with fibre, protein, healthy fats and hydration for steady energy."
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


@api_router.post("/coach")
async def coach(payload: CoachInput, user: Dict[str, Any] = Depends(current_user)):
    profile = await db.profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    system = "You are NutriMitra, a warm bilingual Indian wellness coach. Give practical, non-diagnostic advice. Mention a doctor or dietitian for medical concerns. Keep answers under 120 words."
    prompt = f"User profile: {json.dumps(profile)}\nRespond in {'Telugu' if payload.language == 'te' else 'English'}. User asks: {payload.message}"
    response = await groq_text(system, prompt, user["id"])
    return {"reply": response or "I’m here with you. Try a balanced plate: half colourful vegetables, a quarter protein, and a quarter whole-grain carbohydrate. Tell me what ingredients you have and I’ll make it practical.", "source": "groq" if response else "nutrition guidance"}


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
    return prefs or {"user_id": user["id"], "health_sync": False, "wearables": False, "analytics": False}


@api_router.post("/permissions")
async def set_permissions(payload: Dict[str, bool], user: Dict[str, Any] = Depends(current_user)):
    clean = {key: bool(value) for key, value in payload.items() if key in {"health_sync", "wearables", "analytics"}}
    clean.update({"user_id": user["id"], "updated_at": now_iso()})
    await db.permissions.update_one({"user_id": user["id"]}, {"$set": clean}, upsert=True)
    return clean


app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()