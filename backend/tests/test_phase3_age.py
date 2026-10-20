"""Phase 3 item 4: Wellstride is for adults. Profiles must be 18-100; existing adult profiles keep working."""
import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient

import server

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
MONGO_URL = "mongodb://127.0.0.1:27017"
DB_NAME = "test_database"
FRONTEND = Path(server.__file__).parent.parent / "frontend"

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
def user(mongo):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    resp = s.post(f"{BASE_URL}/api/auth/signup", json={"accept_terms": True, "email": f"age.{uuid.uuid4().hex[:10]}@example.com", "password": "StrongPass123"}, timeout=20)
    assert resp.status_code == 200, resp.text
    s.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    s.user_id = resp.json()["user"]["id"]
    yield s
    mongo.profiles.delete_many({"user_id": s.user_id})
    mongo.users.delete_many({"id": s.user_id})


class TestAgeGate:
    def test_model_bounds(self):
        assert server.ProfileInput(**PROFILE).age == 30
        assert server.ProfileInput(**{**PROFILE, "age": 18}).age == 18
        assert server.ProfileInput(**{**PROFILE, "age": 100}).age == 100
        for bad in (17, 13, 0, -5):
            with pytest.raises(Exception) as info:
                server.ProfileInput(**{**PROFILE, "age": bad})
            assert "You must be 18 or older to use Wellstride." in str(info.value)
        with pytest.raises(Exception):
            server.ProfileInput(**{**PROFILE, "age": 101})

    @pytest.mark.parametrize("age", [17, 16, 13, 1])
    def test_under_18_is_rejected_with_a_clear_message(self, user, mongo, age):
        resp = user.put(f"{BASE_URL}/api/profile", json={**PROFILE, "age": age}, timeout=20)
        assert resp.status_code == 422, resp.text
        detail = resp.json()["detail"]
        assert detail[0]["loc"][-1] == "age"
        assert detail[0]["msg"] == "You must be 18 or older to use Wellstride."
        assert mongo.profiles.count_documents({"user_id": user.user_id}) == 0, "nothing is saved for a minor"

    def test_over_100_is_rejected(self, user):
        resp = user.put(f"{BASE_URL}/api/profile", json={**PROFILE, "age": 101}, timeout=20)
        assert resp.status_code == 422
        assert resp.json()["detail"][0]["msg"] == "Please enter an age of 100 or less."

    @pytest.mark.parametrize("age", [18, 30, 100])
    def test_adult_ages_work(self, user, age):
        resp = user.put(f"{BASE_URL}/api/profile", json={**PROFILE, "age": age}, timeout=20)
        assert resp.status_code == 200, resp.text
        assert user.get(f"{BASE_URL}/api/me", timeout=20).json()["profile"]["age"] == age

    def test_updating_an_adult_profile_to_a_minor_age_is_rejected_and_keeps_the_old_value(self, user):
        assert user.put(f"{BASE_URL}/api/profile", json={**PROFILE, "age": 25}, timeout=20).status_code == 200
        assert user.put(f"{BASE_URL}/api/profile", json={**PROFILE, "age": 15}, timeout=20).status_code == 422
        assert user.get(f"{BASE_URL}/api/me", timeout=20).json()["profile"]["age"] == 25

    def test_existing_adult_account_still_works(self):
        """The long-lived preview account (an adult profile saved before this rule) can still sign in and use the app."""
        s = requests.Session()
        login = s.post(f"{BASE_URL}/api/auth/login", json={"email": "preview.user.2026@example.com", "password": "StrongPass123"}, timeout=20)
        assert login.status_code == 200, login.text
        s.headers["Authorization"] = f"Bearer {login.json()['token']}"
        profile = s.get(f"{BASE_URL}/api/me", timeout=20).json()["profile"]
        assert profile["age"] >= 18
        assert s.get(f"{BASE_URL}/api/dashboard", timeout=20).status_code == 200
        assert s.get(f"{BASE_URL}/api/eat-now", timeout=20).status_code == 200

    def test_a_legacy_minor_profile_still_loads_but_cannot_be_resaved(self, user, mongo):
        """A profile stored under the old 13+ rule is returned as-is (the app sends the user back through
        onboarding), but re-saving it with a minor age fails."""
        mongo.profiles.update_one({"user_id": user.user_id}, {"$set": {"age": 15}})
        assert user.get(f"{BASE_URL}/api/me", timeout=20).json()["profile"]["age"] == 15
        assert user.put(f"{BASE_URL}/api/profile", json={**PROFILE, "age": 15}, timeout=20).status_code == 422
        assert user.put(f"{BASE_URL}/api/profile", json={**PROFILE, "age": 19}, timeout=20).status_code == 200


class TestAgeGateInTheApp:
    """The app has no UI test harness, so check the wiring and both language strings in the source."""

    def read(self, *parts):
        return FRONTEND.joinpath(*parts).read_text(encoding="utf-8")

    def test_onboarding_enforces_18_to_100_before_continuing(self):
        onboarding = self.read("app", "onboarding.tsx")
        assert "age >= 18 && age <= 100" in onboarding and "Number.isInteger(age)" in onboarding
        assert "t.ageMustBe18" in onboarding and "t.ageNote" in onboarding
        assert "onPress={step === 3 ? () => finish() : next}" in onboarding
        assert onboarding.count("ageOk()") >= 2, "checked both when continuing and when finishing"

    def test_both_languages_have_the_note_and_the_message(self):
        english, telugu = self.read("src", "i18n.ts").split("  te: {", 1)
        for key in ("ageNote", "ageMustBe18"):
            assert f"    {key}:" in english and f"    {key}:" in telugu
        assert "18" in re.search(r'ageNote: "([^"]+)"', english).group(1)
        assert "18" in re.search(r'ageNote: "([^"]+)"', telugu).group(1)

    def test_saved_profiles_under_18_go_back_through_onboarding(self):
        assert "Number(result.profile.age) >= 18" in self.read("src", "context", "auth.tsx")

    def test_validation_messages_reach_the_user(self):
        assert "detail[0]?.msg" in self.read("src", "api.ts")
