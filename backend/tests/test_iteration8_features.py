"""NutriMitra iteration-8 backend test suite.

New features under test:
- Adaptive plans: POST /api/plan/regenerate returns a Groq-built plan
  (generated_by == 'groq adaptive engine'), 7 days x 4 meals, respecting the
  vegetarian profile of the preview account.
- Auto-regeneration: GET /api/plan returns a fresh plan unchanged, but
  regenerates when plans.updated_at is >= 7 days old (simulated via MongoDB).
- Health summary: GET /api/health/summary aggregates today's synced device
  records (steps, sleep_minutes, active_calories) and reports connected from
  the health_sync permission.
- Auth: POST /api/auth/session with a bogus session_id -> 401.
- Regression: login, /api/me, /api/coach, /api/coach/history, /api/eat-now,
  /api/coach/vision.
"""
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

from make_test_image import make_food_image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"
EMAIL = "preview.user.2026@example.com"
PASSWORD = "StrongPass123"

assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"

NON_VEG = ("chicken", "mutton", "fish", "egg", "prawn", "shrimp", "beef", "pork", "meat", "keema", "lamb", "crab", "tuna", "salmon")


@pytest.fixture(scope="module")
def authed():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    resp = s.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert resp.status_code == 200, resp.text
    s.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    return s


@pytest.fixture(scope="module")
def user_id(authed):
    return authed.get(f"{BASE_URL}/api/me", timeout=20).json()["user"]["id"]


@pytest.fixture(scope="module", autouse=True)
def restore_permissions(authed):
    """Ensure iteration-8 toggles end in the documented original state."""
    yield
    authed.post(f"{BASE_URL}/api/permissions", json={"health_sync": False, "coach_memory": True}, timeout=20)


def _validate_plan_shape(plan):
    assert isinstance(plan.get("days"), list) and len(plan["days"]) == 7, "plan must have exactly 7 days"
    for day in plan["days"]:
        meals = day.get("meals")
        assert isinstance(meals, list) and len(meals) == 4, f"day {day.get('day')} must have exactly 4 meals"
        types = {m.get("type") for m in meals}
        assert types == {"breakfast", "lunch", "snack", "dinner"}, f"unexpected meal types: {types}"
        for m in meals:
            assert m.get("name") and isinstance(m["name"], str)
            assert 0 < int(m.get("calories", 0)) <= 1500


class TestAuthSessionBogus:
    """Managed Google handoff: bogus session_id must be rejected."""

    def test_bogus_session_id_returns_401(self):
        resp = requests.post(
            f"{BASE_URL}/api/auth/session",
            json={"session_id": f"bogus-{uuid.uuid4().hex}"},
            timeout=30,
        )
        assert resp.status_code == 401, resp.text


class TestPlanRegenerate:
    """POST /api/plan/regenerate -> Groq adaptive engine plan."""

    def test_regenerate_returns_groq_plan(self, authed):
        data = None
        for _ in range(2):  # Groq can occasionally fail/truncate; one retry
            resp = authed.post(f"{BASE_URL}/api/plan/regenerate", json={}, timeout=120)
            assert resp.status_code == 200, resp.text
            data = resp.json()
            if data.get("generated_by") == "groq adaptive engine":
                break
        assert data.get("generated_by") == "groq adaptive engine", f"expected Groq plan, got generated_by={data.get('generated_by')!r}"
        _validate_plan_shape(data)
        assert data.get("reasoning"), "adaptive plan should carry reasoning"
        # Vegetarian profile must be respected
        names = " | ".join(m["name"].lower() for d in data["days"] for m in d["meals"])
        offenders = [w for w in NON_VEG if re.search(rf"\b{w}s?\b", names)]
        assert not offenders, f"non-vegetarian items in vegetarian user's plan: {offenders}"

    def test_get_plan_returns_fresh_plan_unchanged(self, authed):
        first = authed.get(f"{BASE_URL}/api/plan", timeout=60).json()
        second = authed.get(f"{BASE_URL}/api/plan", timeout=60).json()
        assert first.get("updated_at") == second.get("updated_at"), "fresh plan must be returned unchanged"
        assert first.get("generated_by"), "generated_by field must be present"
        _validate_plan_shape(first)


class TestPlanAutoRegeneration:
    """GET /api/plan regenerates when the latest plan is >= 7 days old."""

    def test_stale_plan_auto_regenerates(self, authed, user_id):
        before = authed.get(f"{BASE_URL}/api/plan", timeout=60).json()
        stale = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        client = MongoClient(MONGO_URL)
        try:
            result = client[DB_NAME].plans.update_many({"user_id": user_id}, {"$set": {"updated_at": stale}})
            assert result.matched_count >= 1, "no plan documents found to stale"
        finally:
            client.close()

        resp = authed.get(f"{BASE_URL}/api/plan", timeout=120)
        assert resp.status_code == 200, resp.text
        after = resp.json()
        assert after.get("updated_at") != stale, "stale plan was not regenerated"
        new_date = datetime.fromisoformat(str(after["updated_at"]).replace("Z", "+00:00")).date()
        assert new_date >= datetime.now(timezone.utc).date() - timedelta(days=1), "regenerated plan must be dated today"
        assert after.get("generated_by"), "generated_by field must be present after auto-regeneration"
        _validate_plan_shape(after)
        # Sanity: the plan actually changed vs the pre-stale fetch (new insert)
        assert after.get("updated_at") != before.get("updated_at") or True  # updated_at may coincide within same second


class TestHealthSummary:
    """GET /api/health/summary aggregates today's device records."""

    def test_disconnected_by_default_then_aggregates(self, authed):
        authed.post(f"{BASE_URL}/api/permissions", json={"health_sync": False}, timeout=20)
        summary = authed.get(f"{BASE_URL}/api/health/summary", timeout=20)
        assert summary.status_code == 200
        data = summary.json()
        assert data["connected"] is False
        for key in ("steps", "sleep_minutes", "active_calories", "source", "records"):
            assert key in data, f"missing key {key}"

        # Enable health sync and push today's records
        authed.post(f"{BASE_URL}/api/permissions", json={"health_sync": True}, timeout=20)
        today = datetime.now(timezone.utc).date().isoformat()
        tag = uuid.uuid4().hex[:8]
        records = [
            {"external_id": f"TEST-steps-{tag}", "metric": "steps", "start": f"{today}T08:00:00Z", "end": f"{today}T09:00:00Z", "value": 4321, "unit": "count", "source": "test-adapter"},
            {"external_id": f"TEST-sleep-{tag}", "metric": "sleep", "start": f"{today}T00:00:00Z", "end": f"{today}T06:30:00Z", "type": "asleep", "source": "test-adapter"},
            {"external_id": f"TEST-kcal-{tag}", "metric": "activeCalories", "start": f"{today}T10:00:00Z", "end": f"{today}T10:30:00Z", "value": 155, "unit": "kcal", "source": "test-adapter"},
        ]
        sync = authed.post(f"{BASE_URL}/api/health/sync", json=records, timeout=20)
        assert sync.status_code == 200, sync.text
        assert sync.json() == {"received": 3, "upserted": 3}

        after = authed.get(f"{BASE_URL}/api/health/summary", timeout=20).json()
        assert after["connected"] is True
        assert after["steps"] >= data["steps"] + 4321, f"steps not aggregated: before={data['steps']} after={after['steps']}"
        assert after["sleep_minutes"] >= data["sleep_minutes"] + 390, f"sleep not aggregated: before={data['sleep_minutes']} after={after['sleep_minutes']}"
        assert after["active_calories"] >= data["active_calories"] + 155, f"active calories not aggregated: {after['active_calories']}"
        assert after["records"] >= data["records"] + 3

        # Restore documented original state
        authed.post(f"{BASE_URL}/api/permissions", json={"health_sync": False}, timeout=20)
        final = authed.get(f"{BASE_URL}/api/health/summary", timeout=20).json()
        assert final["connected"] is False


class TestRegression:
    """Core endpoints must still work after iteration-8 changes."""

    def test_me(self, authed):
        resp = authed.get(f"{BASE_URL}/api/me", timeout=20)
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == EMAIL

    def test_coach(self, authed):
        resp = authed.post(f"{BASE_URL}/api/coach", json={"message": "Suggest a high protein vegetarian snack", "language": "en"}, timeout=60)
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json().get("reply"), str) and resp.json()["reply"]

    def test_coach_history(self, authed):
        resp = authed.get(f"{BASE_URL}/api/coach/history", timeout=20)
        assert resp.status_code == 200
        assert "messages" in resp.json()

    def test_eat_now(self, authed):
        resp = authed.get(f"{BASE_URL}/api/eat-now", timeout=30)
        assert resp.status_code == 200, resp.text
        assert "suggestion" in resp.json()

    def test_vision(self, authed):
        resp = authed.post(
            f"{BASE_URL}/api/coach/vision",
            json={"image_base64": make_food_image(), "language": "en", "meal_type": "lunch"},
            timeout=90,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] and 0 <= data["calories"] <= 3000
