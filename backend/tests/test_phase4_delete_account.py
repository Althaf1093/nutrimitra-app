"""Phase 4 item 3: in-app account deletion removes the user and all their data, and their tokens stop working."""
import re
import uuid
from pathlib import Path

import pytest
import requests

import server
from conftest import p4_signup

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "StrongPass123"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def delete(p4, token, **body):
    return requests.delete(f"{p4.url}/api/account", json=body, headers=auth(token), timeout=20)


PROFILE = {"age": 30, "sex": "Prefer not to say", "height_cm": 170, "weight_kg": 70, "target_weight_kg": 65, "conditions": [], "dietary_preferences": ["Vegetarian"], "allergies": [], "disliked_foods": [], "activity_level": "Moderately active", "cooking_time": "20–30 min", "food_budget": "Balanced", "wellness_goal": "Healthier living", "language": "en", "timezone": "Asia/Kolkata"}


def fill_account(p4, p4db):
    """A signed-up person with a row in every per-user collection. Returns (user_id, token, email)."""
    response, email = p4_signup(p4)
    token = response.json()["token"]
    user_id = response.json()["user"]["id"]
    assert requests.put(f"{p4.url}/api/profile", json=PROFILE, headers=auth(token), timeout=20).status_code == 200
    assert requests.put(f"{p4.url}/api/kitchen", json={"items": ["rice", "tomato"], "meals_per_day": 2, "household_size": 3}, headers=auth(token), timeout=20).status_code == 200
    assert requests.post(f"{p4.url}/api/meals", json={"meal_type": "lunch", "name": "Dal", "portion": "1 bowl", "calories": 300, "protein_g": 12, "carbs_g": 40, "fat_g": 8}, headers=auth(token), timeout=20).status_code == 200
    assert requests.post(f"{p4.url}/api/activities", json={"activity_type": "Walk", "duration_min": 20}, headers=auth(token), timeout=20).status_code == 200
    assert requests.post(f"{p4.url}/api/water", json={"delta_ml": 250}, headers=auth(token), timeout=20).status_code == 200
    assert requests.post(f"{p4.url}/api/weight", json={"weight_kg": 69.5}, headers=auth(token), timeout=20).status_code == 200
    assert requests.post(f"{p4.url}/api/permissions", json={"analytics": True}, headers=auth(token), timeout=20).status_code == 200
    assert requests.put(f"{p4.url}/api/reminders", json={"meals": True}, headers=auth(token), timeout=20).status_code == 200
    # Collections that need an AI call or a phone are filled directly.
    p4db.coach_messages.insert_one({"user_id": user_id, "role": "user", "content": "hi", "created_at": "2026-10-19T00:00:00+00:00"})
    p4db.plans.insert_one({"user_id": user_id, "days": [], "updated_at": "2026-10-19T00:00:00+00:00"})
    p4db.health_records.insert_one({"user_id": user_id, "source": "test", "external_id": "x", "start": "2026-10-19T00:00:00+00:00"})
    p4db.password_resets.insert_one({"user_id": user_id, "code_hash": "x" * 64, "attempts": 0, "expires_at": server.datetime.now(server.timezone.utc) + server.timedelta(minutes=30)})
    p4db.email_verifications.insert_one({"user_id": user_id, "code_hash": "y" * 64, "attempts": 0, "expires_at": server.datetime.now(server.timezone.utc) + server.timedelta(minutes=60)})
    p4db.user_sessions.insert_one({"user_id": user_id, "session_token": uuid.uuid4().hex, "expires_at": server.datetime.now(server.timezone.utc) + server.timedelta(days=1)})
    return user_id, token, email


def leftovers(p4db, user_id):
    found = {name: p4db[name].count_documents({"user_id": user_id}) for name in server.USER_DATA_COLLECTIONS}
    found["users"] = p4db.users.count_documents({"id": user_id})
    return {name: count for name, count in found.items() if count}


def test_every_collection_has_data_before_and_none_after(p4, p4db):
    user_id, token, _ = fill_account(p4, p4db)
    before = {name: p4db[name].count_documents({"user_id": user_id}) for name in server.USER_DATA_COLLECTIONS}
    assert all(count >= 1 for count in before.values()), before

    response = delete(p4, token, confirm="DELETE", password=PASSWORD)
    assert response.status_code == 200 and response.json() == {"ok": True}
    assert leftovers(p4db, user_id) == {}


def test_nothing_with_the_user_id_remains_in_any_collection(p4, p4db):
    user_id, token, _ = fill_account(p4, p4db)
    assert delete(p4, token, confirm="DELETE", password=PASSWORD).status_code == 200
    for name in p4db.list_collection_names():
        assert p4db[name].count_documents({"$or": [{"user_id": user_id}, {"id": user_id}]}) == 0, name


def test_tokens_stop_working(p4, p4db):
    user_id, token, email = fill_account(p4, p4db)
    assert requests.get(f"{p4.url}/api/me", headers=auth(token), timeout=20).status_code == 200
    assert delete(p4, token, confirm="DELETE", password=PASSWORD).status_code == 200
    assert requests.get(f"{p4.url}/api/me", headers=auth(token), timeout=20).status_code == 401
    assert delete(p4, token, confirm="DELETE", password=PASSWORD).status_code == 401, "a second delete with the old token is refused"
    login = requests.post(f"{p4.url}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=20)
    assert login.status_code == 401
    # The email can be used to sign up again, as a brand new empty account.
    again, _ = p4_signup(p4, email)
    assert again.status_code == 200 and again.json()["user"]["id"] != user_id


def test_confirmation_is_required(p4, p4db):
    user_id, token, _ = fill_account(p4, p4db)
    assert delete(p4, token).status_code == 422
    assert delete(p4, token, password=PASSWORD).status_code == 422
    assert delete(p4, token, confirm="delete", password=PASSWORD).status_code == 422 or delete(p4, token, confirm="yes", password=PASSWORD).status_code == 422
    assert delete(p4, token, confirm="DELETE", password="wrong-password-1").status_code == 403
    assert delete(p4, token, confirm="DELETE").status_code == 403
    assert leftovers(p4db, user_id) != {}, "nothing is deleted without the right confirmation"
    assert requests.delete(f"{p4.url}/api/account", json={"confirm": "DELETE", "password": PASSWORD}, timeout=20).status_code == 401, "needs a signed-in user"
    assert delete(p4, token, confirm="DELETE", password=PASSWORD).status_code == 200


def test_google_accounts_confirm_with_the_word_alone(p4, p4db):
    user_id = str(uuid.uuid4())
    p4db.users.insert_one({"id": user_id, "email": f"p4.g.{uuid.uuid4().hex[:8]}@example.com", "name": "G", "password_hash": "", "language": "en", "onboarding_complete": False, "consent_version": server.legal.CONSENT_VERSION})
    token = server.issue_token(user_id)
    assert delete(p4, token, confirm="nope").status_code == 422
    assert delete(p4, token, confirm="DELETE").status_code == 200
    assert p4db.users.count_documents({"id": user_id}) == 0


def test_other_people_are_untouched(p4, p4db):
    mine, my_token, _ = fill_account(p4, p4db)
    theirs, their_token, _ = fill_account(p4, p4db)
    before = {name: p4db[name].count_documents({"user_id": theirs}) for name in server.USER_DATA_COLLECTIONS}
    assert delete(p4, my_token, confirm="DELETE", password=PASSWORD).status_code == 200
    assert {name: p4db[name].count_documents({"user_id": theirs}) for name in server.USER_DATA_COLLECTIONS} == before
    assert requests.get(f"{p4.url}/api/me", headers=auth(their_token), timeout=20).status_code == 200
    assert delete(p4, their_token, confirm="DELETE", password=PASSWORD).status_code == 200


def test_the_list_covers_every_collection_the_server_uses():
    """A new per-user collection added to server.py must be added to USER_DATA_COLLECTIONS, or deletion would miss it."""
    source = (ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    used = set(re.findall(r"\bdb\.([a-z_]+)\.", source))
    assert used - {"users"} <= set(server.USER_DATA_COLLECTIONS), used - {"users"} - set(server.USER_DATA_COLLECTIONS)


def test_delete_account_screen_is_in_settings_in_both_languages():
    frontend = ROOT / "frontend"
    settings = (frontend / "app" / "settings.tsx").read_text(encoding="utf-8")
    assert "delete-account-button" in settings and '"/account"' in settings
    i18n = (frontend / "src" / "i18n.ts").read_text(encoding="utf-8")
    for key in ("deleteAccount", "deleteAccountWarning", "deleteTypeDelete", "deleteConfirmButton"):
        assert i18n.count(f"    {key}:") == 2, key
