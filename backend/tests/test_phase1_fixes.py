"""Phase 1 bug-fix regression tests.

Integration tests run against the live server (EXPO_PUBLIC_BACKEND_URL) and the
same MongoDB (test_database). Each module run creates a fresh, isolated user so
results do not depend on what other suites logged for the shared preview user.
Pure helpers are unit-tested by importing server directly.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

import server

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
MONGO_URL = "mongodb://127.0.0.1:27017"
DB_NAME = "test_database"

assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"

PROFILE = {
    "age": 30,
    "sex": "Female",
    "height_cm": 160,
    "weight_kg": 60,
    "target_weight_kg": 58,
    "dietary_preferences": ["Vegetarian"],
    "activity_level": "Moderately active",
    "wellness_goal": "Healthier living",
    "language": "en",
}


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def fresh(mongo):
    """A newly signed-up, onboarded user; all of their data is removed afterwards."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"phase1.{uuid.uuid4().hex[:10]}@example.com"
    resp = s.post(f"{BASE_URL}/api/auth/signup", json={"email": email, "password": "StrongPass123", "name": "Phase One"}, timeout=20)
    assert resp.status_code == 200, resp.text
    s.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    user_id = resp.json()["user"]["id"]
    resp = s.put(f"{BASE_URL}/api/profile", json=PROFILE, timeout=20)
    assert resp.status_code == 200, resp.text
    s.user_id = user_id
    s.email = email
    yield s
    for name in ("plans", "meals", "activities", "weights", "coach_messages", "profiles", "permissions", "reminders", "health_records", "user_sessions"):
        mongo[name].delete_many({"user_id": user_id})
    mongo.users.delete_many({"id": user_id})


def marked_plan(user_id, started_days_ago):
    """A 7-day plan whose meal names reveal which day they belong to."""
    started = datetime.now(timezone.utc) - timedelta(days=started_days_ago)
    days = []
    for number in range(1, 8):
        meals = [
            {"type": meal_type, "name": f"D{number} {meal_type}", "portion": "1 serving", "calories": 400, "protein_g": 20, "carbs_g": 45, "fat_g": 15, "logged": False}
            for meal_type in ("breakfast", "lunch", "snack", "dinner")
        ]
        days.append({"day": number, "title": f"Day {number}", "focus": "Test", "meals": meals})
    return {"user_id": user_id, "goal": "Healthier living", "days": days, "reasoning": "test", "generated_by": "test", "updated_at": started.isoformat()}


class TestPlanDayIndex:
    """Fix 1: the plan advances one day per calendar day instead of always showing Day 1."""

    def test_day_index_helper_wraps_within_plan(self):
        plan = {"days": [{}] * 7, "updated_at": "2026-10-01T10:00:00+00:00"}
        start = datetime(2026, 10, 1).date()
        assert server.plan_day_index(plan, start) == 0
        assert server.plan_day_index(plan, start + timedelta(days=3)) == 3
        assert server.plan_day_index(plan, start + timedelta(days=6)) == 6
        assert server.plan_day_index(plan, start + timedelta(days=9)) == 2
        assert server.plan_day_index({"days": [], "updated_at": "2026-10-01"}, start) == 0
        assert server.plan_day_index({"days": [{}] * 7, "updated_at": "garbage"}, start) == 0

    def test_get_plan_reports_today_index(self, fresh, mongo):
        mongo.plans.delete_many({"user_id": fresh.user_id})
        mongo.plans.insert_one(marked_plan(fresh.user_id, started_days_ago=3))
        resp = fresh.get(f"{BASE_URL}/api/plan", timeout=30)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["today_index"] == 3
        assert body["days"][3]["meals"][0]["name"] == "D4 breakfast"
        assert "user_id" not in body and "_id" not in body

    def test_eat_now_suggests_from_todays_plan_day(self, fresh, mongo):
        mongo.plans.delete_many({"user_id": fresh.user_id})
        mongo.meals.delete_many({"user_id": fresh.user_id})
        mongo.plans.insert_one(marked_plan(fresh.user_id, started_days_ago=5))
        resp = fresh.get(f"{BASE_URL}/api/eat-now", timeout=30)
        assert resp.status_code == 200, resp.text
        assert resp.json()["suggestion"]["name"] == "D6 breakfast"


class TestGoogleAccountLogin:
    """Fix 2: email login against a Google-created account (empty password hash) is a clean 401, not a 500."""

    def test_password_matches_helper(self):
        good = server.bcrypt.hashpw(b"StrongPass123", server.bcrypt.gensalt()).decode()
        assert server.password_matches("StrongPass123", good) is True
        assert server.password_matches("WrongPass123", good) is False
        assert server.password_matches("StrongPass123", "") is False
        assert server.password_matches("StrongPass123", None) is False
        assert server.password_matches("StrongPass123", "not-a-bcrypt-hash") is False

    @pytest.mark.parametrize("stored_hash", ["", "not-a-bcrypt-hash"])
    def test_login_to_passwordless_account_returns_401(self, mongo, stored_hash):
        email = f"google.{uuid.uuid4().hex[:10]}@example.com"
        user_id = str(uuid.uuid4())
        mongo.users.insert_one({"id": user_id, "email": email, "name": "Google User", "password_hash": stored_hash, "language": "en", "onboarding_complete": False, "created_at": datetime.now(timezone.utc).isoformat()})
        try:
            resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "AnyPassword123"}, timeout=20)
            assert resp.status_code == 401, resp.text
            assert resp.json()["detail"] == "Email or password is incorrect"
        finally:
            mongo.users.delete_many({"id": user_id})
