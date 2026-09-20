"""NutriMitra iteration-6 backend test suite.

Covers the new features from the expo-router refactor iteration:
- Email/password login with preview account
- GET /api/eat-now (suggestion + calorie math)
- POST /api/coach/vision (food photo recognition, Groq-or-Emergent fallback)
- GET/PUT /api/reminders persistence
- POST /api/health/sync idempotent upsert
- POST /api/auth/session invalid session_id -> 401
- Regression: /api/plan, /api/dashboard, /api/coach, /api/progress, POST /api/meals
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
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def token(session):
    """Login once; all authenticated tests reuse the JWT."""
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest.fixture(scope="module")
def authed(session, token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return s


class TestAuth:
    """Auth endpoints: login + managed Google session exchange."""

    def test_login_returns_token_and_user(self, session):
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("token"), str) and len(data["token"]) > 20
        assert data["user"]["email"] == EMAIL
        assert data["user"]["onboarding_complete"] is True

    def test_login_wrong_password_rejected(self, session):
        resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": "WrongPass999"}, timeout=20)
        assert resp.status_code == 401

    def test_google_session_invalid_id_returns_401(self, session):
        resp = session.post(f"{BASE_URL}/api/auth/session", json={"session_id": "invalid-test-session-000"}, timeout=30)
        assert resp.status_code == 401, resp.text

    def test_me_unauthenticated_returns_401(self, session):
        resp = session.get(f"{BASE_URL}/api/me", timeout=20)
        assert resp.status_code == 401

    def test_me_with_jwt(self, authed):
        resp = authed.get(f"{BASE_URL}/api/me", timeout=20)
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == EMAIL
        assert resp.json()["profile"] is not None


class TestEatNow:
    """What Should I Eat Now endpoint."""

    def test_eat_now_shape_and_math(self, authed):
        resp = authed.get(f"{BASE_URL}/api/eat-now", timeout=30)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data.get("suggestion"), dict)
        for key in ("name", "calories", "protein_g", "carbs_g", "fat_g", "portion"):
            assert key in data["suggestion"], f"missing suggestion.{key}"
        assert data["target_calories"] >= 1200
        assert data["remaining_calories"] == max(0, data["target_calories"] - data["consumed_calories"])


class TestCoachVision:
    """Food-photo recognition: Groq vision (none on key) -> Emergent fallback."""

    def test_vision_returns_structured_nutrition(self, authed):
        image_b64 = make_food_image()
        resp = authed.post(
            f"{BASE_URL}/api/coach/vision",
            json={"image_base64": image_b64, "language": "en", "meal_type": "lunch"},
            timeout=90,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        for key in ("name", "portion", "calories", "protein_g", "carbs_g", "fat_g", "confidence", "alternatives", "model"):
            assert key in data, f"missing {key}"
        assert data["model"], "model field must be present"
        assert data["confidence"] in {"low", "medium", "high"}
        assert 0 <= data["calories"] <= 3000
        assert isinstance(data["alternatives"], list)
        assert data["meal_type"] == "lunch"

    def test_vision_rejects_tiny_image(self, authed):
        resp = authed.post(f"{BASE_URL}/api/coach/vision", json={"image_base64": "aGk=", "language": "en"}, timeout=20)
        assert resp.status_code == 422


class TestReminders:
    """Reminder prefs GET/PUT persistence."""

    def test_get_defaults_then_put_and_verify(self, authed):
        get_resp = authed.get(f"{BASE_URL}/api/reminders", timeout=20)
        assert get_resp.status_code == 200
        original = get_resp.json()
        toggled = {"meals": not original.get("meals", True), "hydration": True, "movement": False, "weekly": not original.get("weekly", True)}
        put_resp = authed.put(f"{BASE_URL}/api/reminders", json=toggled, timeout=20)
        assert put_resp.status_code == 200, put_resp.text
        assert put_resp.json()["hydration"] is True
        # Re-GET to confirm persistence
        verify = authed.get(f"{BASE_URL}/api/reminders", timeout=20)
        assert verify.status_code == 200
        for key, value in toggled.items():
            assert verify.json()[key] == value, f"{key} not persisted"
        # restore original
        authed.put(f"{BASE_URL}/api/reminders", json={k: original.get(k, True) for k in ("meals", "hydration", "movement", "weekly")}, timeout=20)


class TestHealthSync:
    """Idempotent health record ingestion."""

    def test_upsert_idempotency(self, authed):
        perm = authed.post(f"{BASE_URL}/api/permissions", json={"health_sync": True}, timeout=20)
        assert perm.status_code == 200, perm.text
        record = {
            "external_id": f"TEST-{uuid.uuid4().hex[:12]}",
            "metric": "steps",
            "start": "2026-01-10T08:00:00Z",
            "end": "2026-01-10T09:00:00Z",
            "value": 4200,
            "unit": "count",
            "source": "test-adapter",
        }
        first = authed.post(f"{BASE_URL}/api/health/sync", json=[record], timeout=20)
        assert first.status_code == 200, first.text
        assert first.json() == {"received": 1, "upserted": 1}
        second = authed.post(f"{BASE_URL}/api/health/sync", json=[record], timeout=20)
        assert second.status_code == 200
        assert second.json() == {"received": 1, "upserted": 0}, "second identical record should update, not upsert"


class TestRegression:
    """Core endpoints that existed before the refactor must still work."""

    def test_plan(self, authed):
        resp = authed.get(f"{BASE_URL}/api/plan", timeout=45)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("days", [])) == 7
        assert len(data["days"][0]["meals"]) == 4

    def test_dashboard(self, authed):
        resp = authed.get(f"{BASE_URL}/api/dashboard", timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        assert "readiness" in data and "meals" in data and "activities" in data

    def test_progress(self, authed):
        resp = authed.get(f"{BASE_URL}/api/progress", timeout=30)
        assert resp.status_code == 200
        assert "weights" in resp.json()

    def test_meals_post_and_reflect_in_dashboard(self, authed):
        resp = authed.post(
            f"{BASE_URL}/api/meals",
            json={"meal_type": "snack", "name": "TEST iteration6 sprouts", "calories": 110, "protein_g": 6, "carbs_g": 12, "fat_g": 3, "source": "manual"},
            timeout=20,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "TEST iteration6 sprouts"
        dash = authed.get(f"{BASE_URL}/api/dashboard", timeout=30).json()
        assert any(m.get("name") == "TEST iteration6 sprouts" for m in dash["meals"])

    def test_coach_reply(self, authed):
        resp = authed.post(f"{BASE_URL}/api/coach", json={"message": "Suggest a light dinner", "language": "en"}, timeout=60)
        assert resp.status_code == 200
        assert isinstance(resp.json().get("reply"), str) and len(resp.json()["reply"]) > 20
