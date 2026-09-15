"""NutriMitra iteration-7 backend test suite.

New features under test:
- Coach conversation memory: POST /api/coach persists exchanges to db.coach_messages
  only when coach_memory permission is enabled; GET /api/coach/history returns
  stored messages (empty when memory off).
- Structured recipe cards: POST /api/coach can return a parsed {recipe} object.
- Privacy-first health sync: POST /api/health/sync returns 403 unless health_sync
  permission is enabled via POST /api/permissions; idempotent once enabled.
- Regression: login, /api/eat-now, /api/plan, /api/dashboard, /api/coach/vision,
  /api/reminders.
"""
import os
import uuid

import pytest
import requests

from make_test_image import make_food_image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
EMAIL = "preview.user.2026@example.com"
PASSWORD = "StrongPass123"

assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"


@pytest.fixture(scope="module")
def authed():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    resp = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert resp.status_code == 200, resp.text
    s.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    return s


@pytest.fixture(scope="module")
def perms(authed):
    """Snapshot original permissions so each class can restore them."""
    resp = authed.get(f"{BASE_URL}/api/permissions", timeout=20)
    assert resp.status_code == 200
    original = resp.json()
    yield authed
    restore = {k: bool(original.get(k, False)) for k in ("health_sync", "wearables", "analytics", "coach_memory")}
    authed.post(f"{BASE_URL}/api/permissions", json=restore, timeout=20)


class TestHealthSyncPermissionGate:
    """health/sync must 403 until health_sync permission is enabled."""

    def _record(self):
        return {
            "external_id": f"TEST-{uuid.uuid4().hex[:12]}",
            "metric": "steps",
            "start": "2026-01-10T08:00:00Z",
            "end": "2026-01-10T09:00:00Z",
            "value": 3100,
            "unit": "count",
            "source": "test-adapter",
        }

    def test_forbidden_when_disabled_then_ok_when_enabled(self, perms):
        perms.post(f"{BASE_URL}/api/permissions", json={"health_sync": False}, timeout=20)
        record = self._record()
        denied = perms.post(f"{BASE_URL}/api/health/sync", json=[record], timeout=20)
        assert denied.status_code == 403, denied.text

        perms.post(f"{BASE_URL}/api/permissions", json={"health_sync": True}, timeout=20)
        first = perms.post(f"{BASE_URL}/api/health/sync", json=[record], timeout=20)
        assert first.status_code == 200, first.text
        assert first.json() == {"received": 1, "upserted": 1}
        second = perms.post(f"{BASE_URL}/api/health/sync", json=[record], timeout=20)
        assert second.status_code == 200
        assert second.json() == {"received": 1, "upserted": 0}, "identical record must update, not upsert"


class TestCoachMemory:
    """Coach memory: history persisted only when coach_memory enabled."""

    def test_history_reflects_messages_when_memory_on(self, perms):
        perms.post(f"{BASE_URL}/api/permissions", json={"coach_memory": True}, timeout=20)
        marker = f"TEST-marker-{uuid.uuid4().hex[:8]}"
        r1 = perms.post(f"{BASE_URL}/api/coach", json={"message": f"I am vegetarian ({marker}). Remember this.", "language": "en"}, timeout=60)
        assert r1.status_code == 200, r1.text
        assert r1.json()["memory"] is True

        r2 = perms.post(f"{BASE_URL}/api/coach", json={"message": "What dinner suits me given what I just told you?", "language": "en"}, timeout=60)
        assert r2.status_code == 200, r2.text
        reply2 = r2.json()["reply"].lower()
        assert "vegetarian" in reply2 or "veg " in reply2 or "paneer" in reply2 or "dal" in reply2, f"reply did not reflect context: {reply2[:200]}"

        hist = perms.get(f"{BASE_URL}/api/coach/history", timeout=20)
        assert hist.status_code == 200
        data = hist.json()
        assert data["memory"] is True
        texts = [m["text"] for m in data["messages"]]
        assert any(marker in t for t in texts), "user message not persisted"
        assert any(m["role"] == "coach" for m in data["messages"]), "coach reply not persisted"

    def test_memory_off_returns_empty_and_stores_nothing(self, perms):
        perms.post(f"{BASE_URL}/api/permissions", json={"coach_memory": False}, timeout=20)
        hist = perms.get(f"{BASE_URL}/api/coach/history", timeout=20)
        assert hist.status_code == 200
        data = hist.json()
        assert data["memory"] is False
        assert data["messages"] == [], "history must be hidden while memory off"

        before = perms.post(f"{BASE_URL}/api/permissions", json={"coach_memory": True}, timeout=20)
        assert before.status_code == 200
        count_before = len(perms.get(f"{BASE_URL}/api/coach/history", timeout=20).json()["messages"])
        perms.post(f"{BASE_URL}/api/permissions", json={"coach_memory": False}, timeout=20)

        r = perms.post(f"{BASE_URL}/api/coach", json={"message": "TEST do not store this", "language": "en"}, timeout=60)
        assert r.status_code == 200
        assert r.json()["memory"] is False

        perms.post(f"{BASE_URL}/api/permissions", json={"coach_memory": True}, timeout=20)
        count_after = len(perms.get(f"{BASE_URL}/api/coach/history", timeout=20).json()["messages"])
        assert count_after == count_before, "messages were stored while coach_memory disabled"


class TestCoachRecipe:
    """Recipe card: POST /api/coach parses fenced ```recipe JSON block."""

    def test_recipe_request_returns_structured_card(self, perms):
        perms.post(f"{BASE_URL}/api/permissions", json={"coach_memory": True}, timeout=20)
        recipe = None
        last_text = ""
        for _ in range(2):  # LLM output is non-deterministic; retry once
            resp = perms.post(
                f"{BASE_URL}/api/coach",
                json={"message": "Share a quick healthy Indian dinner recipe I can cook tonight.", "language": "en"},
                timeout=90,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            last_text = data["reply"]
            if data.get("recipe"):
                recipe = data["recipe"]
                break
        if not recipe:
            pytest.skip(f"Groq did not emit a recipe block this run; reply={last_text[:200]}")
        assert isinstance(recipe["name"], str) and recipe["name"]
        assert 1 <= recipe["time_min"] <= 180
        assert recipe["calories"] > 0
        assert isinstance(recipe["ingredients"], list) and recipe["ingredients"]
        assert isinstance(recipe["steps"], list) and recipe["steps"]
        assert "```recipe" not in last_text, "raw recipe fence leaked into reply text"

        # Log the recipe as a meal and verify persistence in dashboard
        meal = perms.post(
            f"{BASE_URL}/api/meals",
            json={"meal_type": "dinner", "name": f"TEST {recipe['name']}", "calories": recipe["calories"],
                  "protein_g": recipe["protein_g"], "carbs_g": recipe["carbs_g"], "fat_g": recipe["fat_g"],
                  "source": "coach recipe"},
            timeout=20,
        )
        assert meal.status_code == 200
        dash = perms.get(f"{BASE_URL}/api/dashboard", timeout=30).json()
        assert any(m.get("name") == f"TEST {recipe['name']}" for m in dash["meals"])


class TestRegression:
    """Core endpoints must still work after iteration-7 changes."""

    def test_eat_now(self, authed):
        resp = authed.get(f"{BASE_URL}/api/eat-now", timeout=30)
        assert resp.status_code == 200, resp.text
        assert "suggestion" in resp.json()

    def test_plan(self, authed):
        resp = authed.get(f"{BASE_URL}/api/plan", timeout=45)
        assert resp.status_code == 200
        assert len(resp.json().get("days", [])) == 7

    def test_dashboard(self, authed):
        resp = authed.get(f"{BASE_URL}/api/dashboard", timeout=30)
        assert resp.status_code == 200
        assert "readiness" in resp.json()

    def test_reminders_roundtrip(self, authed):
        original = authed.get(f"{BASE_URL}/api/reminders", timeout=20).json()
        toggled = {"meals": original.get("meals", True), "hydration": not original.get("hydration", False),
                   "movement": original.get("movement", False), "weekly": original.get("weekly", True)}
        put = authed.put(f"{BASE_URL}/api/reminders", json=toggled, timeout=20)
        assert put.status_code == 200
        assert authed.get(f"{BASE_URL}/api/reminders", timeout=20).json()["hydration"] == toggled["hydration"]
        authed.put(f"{BASE_URL}/api/reminders", json={k: original.get(k, True) for k in ("meals", "hydration", "movement", "weekly")}, timeout=20)

    def test_vision_still_works(self, authed):
        resp = authed.post(
            f"{BASE_URL}/api/coach/vision",
            json={"image_base64": make_food_image(), "language": "en", "meal_type": "lunch"},
            timeout=90,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] and 0 <= data["calories"] <= 3000 and data["model"]
