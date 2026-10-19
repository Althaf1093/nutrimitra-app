"""Phase 1 bug-fix regression tests.

Integration tests run against the live server (EXPO_PUBLIC_BACKEND_URL) and the
same MongoDB (test_database). Each module run creates a fresh, isolated user so
results do not depend on what other suites logged for the shared preview user.
Pure helpers are unit-tested by importing server directly.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

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


class TestUserTimezone:
    """Fix 3: "today" follows the user's profile timezone (India by default), not UTC."""

    def test_zone_helpers(self):
        assert str(server.user_zone(None)) == "Asia/Kolkata"
        assert str(server.user_zone({"timezone": "Europe/London"})) == "Europe/London"
        assert str(server.user_zone({"timezone": "Not/AZone"})) == "Asia/Kolkata"
        # A plan created at 20:00 UTC on Oct 1 starts on Oct 2 in India.
        plan = {"days": [{}] * 7, "updated_at": "2026-10-01T20:00:00+00:00"}
        india = server.ZoneInfo("Asia/Kolkata")
        assert str(server.plan_start_date(plan, india)) == "2026-10-02"
        assert server.plan_day_index(plan, datetime(2026, 10, 2).date(), india) == 0

    def test_profile_timezone_default_and_validation(self, fresh):
        assert server.ProfileInput(**PROFILE).timezone == "Asia/Kolkata"
        assert server.ProfileInput(**PROFILE, timezone="Not/AZone").timezone == "Asia/Kolkata"
        resp = fresh.put(f"{BASE_URL}/api/profile", json={**PROFILE, "timezone": "America/New_York"}, timeout=20)
        assert resp.status_code == 200, resp.text
        assert resp.json()["profile"]["timezone"] == "America/New_York"
        me = fresh.get(f"{BASE_URL}/api/me", timeout=20).json()
        assert me["profile"]["timezone"] == "America/New_York"

    @pytest.mark.parametrize("zone_name", ["Asia/Kolkata", "Pacific/Kiritimati", "Pacific/Pago_Pago"])
    def test_logs_and_dashboard_use_local_date(self, fresh, mongo, zone_name):
        resp = fresh.put(f"{BASE_URL}/api/profile", json={**PROFILE, "timezone": zone_name}, timeout=20)
        assert resp.status_code == 200, resp.text
        local_date = datetime.now(server.ZoneInfo(zone_name)).date().isoformat()
        meal = fresh.post(f"{BASE_URL}/api/meals", json={"meal_type": "snack", "name": f"TZ {zone_name}", "calories": 100, "protein_g": 3, "carbs_g": 10, "fat_g": 4}, timeout=20)
        assert meal.status_code == 200, meal.text
        assert meal.json()["date"] == local_date
        activity = fresh.post(f"{BASE_URL}/api/activities", json={"activity_type": "Walking", "duration_min": 10, "active_calories": 40}, timeout=20)
        assert activity.json()["date"] == local_date
        weight = fresh.post(f"{BASE_URL}/api/weight", json={"weight_kg": 60}, timeout=20)
        assert weight.json()["date"] == local_date
        dash = fresh.get(f"{BASE_URL}/api/dashboard", timeout=20).json()
        assert dash["date"] == local_date
        assert any(item["name"] == f"TZ {zone_name}" for item in dash["meals"])
        eat = fresh.get(f"{BASE_URL}/api/eat-now", timeout=20).json()
        assert eat["consumed_calories"] >= 100
        mongo.meals.delete_many({"user_id": fresh.user_id})
        mongo.activities.delete_many({"user_id": fresh.user_id})
        mongo.weights.delete_many({"user_id": fresh.user_id})
        fresh.put(f"{BASE_URL}/api/profile", json=PROFILE, timeout=20)


@pytest.fixture(scope="module")
def other_user(mongo):
    """A second account, to prove log entries cannot be changed across users."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    resp = s.post(f"{BASE_URL}/api/auth/signup", json={"email": f"phase1.other.{uuid.uuid4().hex[:10]}@example.com", "password": "StrongPass123"}, timeout=20)
    assert resp.status_code == 200, resp.text
    s.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    user_id = resp.json()["user"]["id"]
    yield s
    mongo.users.delete_many({"id": user_id})


class TestCorrectableLogs:
    """Fix 4: meals, activities and weights can be deleted (meals edited), scoped to their owner;
    plan meals are flagged as logged and cannot be logged twice in a day."""

    MEAL = {"meal_type": "lunch", "name": "Correctable dal", "calories": 450, "protein_g": 18, "carbs_g": 60, "fat_g": 12, "source": "manual"}

    def test_delete_meal(self, fresh, other_user):
        meal = fresh.post(f"{BASE_URL}/api/meals", json=self.MEAL, timeout=20).json()
        assert other_user.delete(f"{BASE_URL}/api/meals/{meal['id']}", timeout=20).status_code == 404
        resp = fresh.delete(f"{BASE_URL}/api/meals/{meal['id']}", timeout=20)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"deleted": True, "id": meal["id"]}
        dash = fresh.get(f"{BASE_URL}/api/dashboard", timeout=20).json()
        assert all(item["id"] != meal["id"] for item in dash["meals"])
        assert fresh.delete(f"{BASE_URL}/api/meals/{meal['id']}", timeout=20).status_code == 404

    def test_patch_meal(self, fresh, other_user):
        meal = fresh.post(f"{BASE_URL}/api/meals", json=self.MEAL, timeout=20).json()
        assert other_user.patch(f"{BASE_URL}/api/meals/{meal['id']}", json={"calories": 1}, timeout=20).status_code == 404
        resp = fresh.patch(f"{BASE_URL}/api/meals/{meal['id']}", json={"calories": 300, "name": "Smaller dal"}, timeout=20)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["calories"] == 300 and body["name"] == "Smaller dal" and body["protein_g"] == 18
        assert "_id" not in body
        assert fresh.patch(f"{BASE_URL}/api/meals/{meal['id']}", json={}, timeout=20).status_code == 400
        assert fresh.patch(f"{BASE_URL}/api/meals/{meal['id']}", json={"calories": -5}, timeout=20).status_code == 422
        fresh.delete(f"{BASE_URL}/api/meals/{meal['id']}", timeout=20)

    def test_delete_activity_and_weight(self, fresh, other_user):
        activity = fresh.post(f"{BASE_URL}/api/activities", json={"activity_type": "Walking", "duration_min": 20, "active_calories": 80}, timeout=20).json()
        assert other_user.delete(f"{BASE_URL}/api/activities/{activity['id']}", timeout=20).status_code == 404
        assert fresh.delete(f"{BASE_URL}/api/activities/{activity['id']}", timeout=20).status_code == 200
        assert fresh.delete(f"{BASE_URL}/api/activities/{activity['id']}", timeout=20).status_code == 404
        weight = fresh.post(f"{BASE_URL}/api/weight", json={"weight_kg": 61.2}, timeout=20).json()
        assert other_user.delete(f"{BASE_URL}/api/weight/{weight['id']}", timeout=20).status_code == 404
        assert fresh.delete(f"{BASE_URL}/api/weight/{weight['id']}", timeout=20).status_code == 200
        progress = fresh.get(f"{BASE_URL}/api/progress", timeout=20).json()
        assert all(item["id"] != weight["id"] for item in progress["weights"])

    def test_delete_requires_auth(self):
        assert requests.delete(f"{BASE_URL}/api/meals/anything", timeout=20).status_code == 401

    def test_plan_meal_logged_flag_and_duplicate_guard(self, fresh, mongo):
        mongo.plans.delete_many({"user_id": fresh.user_id})
        mongo.meals.delete_many({"user_id": fresh.user_id})
        mongo.plans.insert_one(marked_plan(fresh.user_id, started_days_ago=2))
        plan = fresh.get(f"{BASE_URL}/api/plan", timeout=30).json()
        assert plan["today_index"] == 2
        assert not any(meal["logged"] for day in plan["days"] for meal in day["meals"])

        breakfast = plan["days"][2]["meals"][0]
        payload = {"meal_type": breakfast["type"], "name": breakfast["name"], "calories": breakfast["calories"], "protein_g": breakfast["protein_g"], "carbs_g": breakfast["carbs_g"], "fat_g": breakfast["fat_g"], "source": "plan"}
        logged = fresh.post(f"{BASE_URL}/api/meals", json=payload, timeout=20)
        assert logged.status_code == 200, logged.text
        duplicate = fresh.post(f"{BASE_URL}/api/meals", json=payload, timeout=20)
        assert duplicate.status_code == 409, duplicate.text

        plan = fresh.get(f"{BASE_URL}/api/plan", timeout=30).json()
        flags = {meal["name"]: meal["logged"] for meal in plan["days"][2]["meals"]}
        assert flags == {"D3 breakfast": True, "D3 lunch": False, "D3 snack": False, "D3 dinner": False}
        # Only today's day is flagged; the stored plan itself is not mutated.
        assert not any(meal["logged"] for index, day in enumerate(plan["days"]) if index != 2 for meal in day["meals"])

        # Deleting the log entry un-flags the plan meal and allows logging it again.
        assert fresh.delete(f"{BASE_URL}/api/meals/{logged.json()['id']}", timeout=20).status_code == 200
        plan = fresh.get(f"{BASE_URL}/api/plan", timeout=30).json()
        assert plan["days"][2]["meals"][0]["logged"] is False
        assert fresh.post(f"{BASE_URL}/api/meals", json=payload, timeout=20).status_code == 200
        mongo.meals.delete_many({"user_id": fresh.user_id})


class TestFallbackCalories:
    """Fix 5: fallback meals are sized from the user's calorie target instead of a fixed 430 kcal / 24 g."""

    def test_calorie_target_matches_formula(self):
        # Female, 30 y, 160 cm, 60 kg, moderately active: (600 + 1000 - 150 - 161) * 1.55 = 1997.95
        assert server.calorie_target(PROFILE) == 1997
        assert server.calorie_target({**PROFILE, "wellness_goal": "Weight loss"}) == 1597
        assert server.calorie_target({**PROFILE, "weight_kg": 30, "height_cm": 120, "age": 80}) == 1200

    def test_meals_vary_by_type_and_day(self):
        plan = server.local_plan(PROFILE)
        day_one = {meal["type"]: meal for meal in plan["days"][0]["meals"]}
        assert len({meal["calories"] for meal in day_one.values()}) == 4
        assert day_one["snack"]["calories"] < day_one["breakfast"]["calories"] < day_one["dinner"]["calories"] < day_one["lunch"]["calories"]
        daily_totals = [sum(meal["calories"] for meal in day["meals"]) for day in plan["days"]]
        assert len(set(daily_totals)) > 1, "every fallback day has identical calories"
        week_average = sum(daily_totals) / len(daily_totals)
        assert abs(week_average - server.calorie_target(PROFILE)) / server.calorie_target(PROFILE) < 0.03
        assert all(meal["calories"] != 430 for day in plan["days"] for meal in day["meals"])

    def test_meals_scale_with_target_and_goal(self):
        small = server.portion_for({**PROFILE, "wellness_goal": "Weight loss"}, "lunch")
        large = server.portion_for({**PROFILE, "sex": "Male", "weight_kg": 85, "height_cm": 180, "activity_level": "Very active", "wellness_goal": "Muscle building"}, "lunch")
        assert large["calories"] > small["calories"] * 1.5
        assert large["protein_g"] > small["protein_g"]
        for meal in (small, large):
            energy = 4 * meal["protein_g"] + 4 * meal["carbs_g"] + 9 * meal["fat_g"]
            assert abs(energy - meal["calories"]) / meal["calories"] < 0.05, meal
            assert 0 < meal["calories"] <= 1500


class FakeGroq(BaseHTTPRequestHandler):
    """Stand-in for the Groq API. mode "busy": always 429; "flaky": one 429, then a normal answer."""

    state = {"mode": "busy", "hits": 0}

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        FakeGroq.state["hits"] += 1
        if FakeGroq.state["mode"] == "busy" or FakeGroq.state["hits"] == 1:
            body, code = b'{"error": {"message": "Rate limit reached"}}', 429
        else:
            body, code = json.dumps({"choices": [{"message": {"content": "Fake coach answer"}}]}).encode(), 200
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Retry-After", "0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def busy_backend():
    """A second backend on the same database whose AI provider is the fake above."""
    fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeGroq)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    port = free_port()
    env = {**os.environ, "GROQ_API_KEY": "fake-key", "GROQ_BASE_URL": f"http://127.0.0.1:{fake.server_address[1]}"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)], cwd=Path(server.__file__).parent, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if requests.get(f"{url}/api/", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                time.sleep(0.5)
        else:
            pytest.fail("busy backend did not start")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=20)
        fake.shutdown()


class TestAIBusy:
    """Fix 6: Groq 429s are retried with backoff (max 2 retries), then surface as a structured
    "ai_busy" error instead of a silent canned reply or a silently swapped plan."""

    def test_retry_delay_backs_off_and_caps(self):
        response = server.httpx.Response(429)
        assert server.retry_delay(response, 0) == 1.0
        assert server.retry_delay(response, 1) == 2.0
        assert server.retry_delay(server.httpx.Response(429, headers={"Retry-After": "5"}), 0) == 5.0
        assert server.retry_delay(server.httpx.Response(429, headers={"Retry-After": "600"}), 0) == 10.0

    def test_coach_returns_ai_busy_after_two_retries(self, busy_backend, fresh, mongo):
        FakeGroq.state.update(mode="busy", hits=0)
        resp = fresh.post(f"{busy_backend}/api/coach", json={"message": "Breakfast idea?", "language": "en"}, timeout=60)
        assert resp.status_code == 503, resp.text
        assert resp.json()["detail"]["code"] == "ai_busy"
        assert "try again" in resp.json()["detail"]["message"].lower()
        assert resp.headers.get("retry-after") == "60"
        assert FakeGroq.state["hits"] == 3, "expected the first attempt plus exactly 2 retries"
        assert mongo.coach_messages.count_documents({"user_id": fresh.user_id}) == 0, "a failed exchange must not be stored"

    def test_coach_recovers_when_a_retry_succeeds(self, busy_backend, fresh, mongo):
        FakeGroq.state.update(mode="flaky", hits=0)
        resp = fresh.post(f"{busy_backend}/api/coach", json={"message": "Breakfast idea?", "language": "en"}, timeout=60)
        assert resp.status_code == 200, resp.text
        assert resp.json()["reply"] == "Fake coach answer"
        assert FakeGroq.state["hits"] == 2
        mongo.coach_messages.delete_many({"user_id": fresh.user_id})

    def test_regenerate_returns_ai_busy_and_keeps_existing_plan(self, busy_backend, fresh, mongo):
        mongo.plans.delete_many({"user_id": fresh.user_id})
        mongo.plans.insert_one(marked_plan(fresh.user_id, started_days_ago=1))
        FakeGroq.state.update(mode="busy", hits=0)
        resp = fresh.post(f"{busy_backend}/api/plan/regenerate", json={}, timeout=60)
        assert resp.status_code == 503, resp.text
        assert resp.json()["detail"]["code"] == "ai_busy"
        assert mongo.plans.count_documents({"user_id": fresh.user_id}) == 1
        assert fresh.get(f"{busy_backend}/api/plan", timeout=30).json()["days"][0]["meals"][0]["name"] == "D1 breakfast"

    def test_first_plan_while_busy_is_flagged_and_not_saved(self, busy_backend, fresh, mongo):
        mongo.plans.delete_many({"user_id": fresh.user_id})
        FakeGroq.state.update(mode="busy", hits=0)
        resp = fresh.get(f"{busy_backend}/api/plan", timeout=60)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ai_status"] == "ai_busy" and body["ai_message"]
        assert len(body["days"]) == 7 and body["today_index"] == 0
        assert mongo.plans.count_documents({"user_id": fresh.user_id}) == 0, "a busy fallback must not stick for a week"

    def test_stale_plan_while_busy_is_kept(self, busy_backend, fresh, mongo):
        mongo.plans.delete_many({"user_id": fresh.user_id})
        mongo.plans.insert_one(marked_plan(fresh.user_id, started_days_ago=9))
        FakeGroq.state.update(mode="busy", hits=0)
        body = fresh.get(f"{busy_backend}/api/plan", timeout=60).json()
        assert body["ai_status"] == "ai_busy"
        assert body["today_index"] == 2 and body["days"][2]["meals"][0]["name"] == "D3 breakfast"
        mongo.plans.delete_many({"user_id": fresh.user_id})


class TestPlanPrompt:
    """Fix 7: the plan prompt's JSON schema quotes every key (it had "fat_g: number)."""

    def test_every_schema_key_is_quoted(self):
        schema = server.PLAN_SYSTEM[server.PLAN_SYSTEM.index("{"):server.PLAN_SYSTEM.rindex("}") + 1]
        for key in ("days", "day", "title", "focus", "meals", "type", "name", "portion", "calories", "protein_g", "carbs_g", "fat_g", "reasoning"):
            assert f'"{key}":' in schema, key
        assert '"fat_g: ' not in schema
        assert schema.count('"') % 2 == 0, "unbalanced quotes in the plan schema"
