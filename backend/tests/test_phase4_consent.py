"""Phase 4 item 2: consent at signup (and Google first use), stored with a version and time; existing accounts asked once."""
import uuid
from pathlib import Path

import pytest
import requests

import legal
import server
from conftest import p4_signup

ROOT = Path(__file__).resolve().parents[2]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cleanup(p4db):
    emails = []
    yield emails
    for email in emails:
        user = p4db.users.find_one({"email": email})
        if user:
            for name in p4db.list_collection_names():
                p4db[name].delete_many({"user_id": user["id"]})
            p4db.users.delete_one({"id": user["id"]})


def test_signup_without_consent_is_rejected(p4, p4db, cleanup):
    email = f"p4.{uuid.uuid4().hex[:10]}@example.com"
    cleanup.append(email)
    for extra in ({"accept_terms": False}, {"accept_terms": None}):
        response, _ = p4_signup(p4, email, **extra)
        assert response.status_code == 422, extra
    omitted = requests.post(f"{p4.url}/api/auth/signup", json={"email": email, "password": "StrongPass123"}, timeout=20)
    assert omitted.status_code == 422
    assert omitted.json()["detail"]["code"] == "consent_required"
    assert "18 or over" in omitted.json()["detail"]["message"]
    assert p4db.users.find_one({"email": email}) is None, "no account is created without consent"


def test_signup_stores_consent_version_and_time(p4, p4db, cleanup):
    response, email = p4_signup(p4)
    cleanup.append(email)
    assert response.status_code == 200
    user = p4db.users.find_one({"email": email})
    assert user["consent_version"] == legal.CONSENT_VERSION
    assert user["consent_at"].startswith("20")
    body = response.json()["user"]
    assert body["consent_version"] == legal.CONSENT_VERSION and body["needs_consent"] is False


def test_client_cannot_choose_the_consent_version(p4, p4db, cleanup):
    response, email = p4_signup(p4, consent_version="1999-01-01")
    cleanup.append(email)
    assert response.status_code == 200
    assert p4db.users.find_one({"email": email})["consent_version"] == legal.CONSENT_VERSION


def test_existing_account_is_asked_once(p4, p4db, cleanup):
    response, email = p4_signup(p4)
    cleanup.append(email)
    token = response.json()["token"]
    # An account from before consent existed: no consent fields at all.
    p4db.users.update_one({"email": email}, {"$unset": {"consent_version": "", "consent_at": ""}})
    me = requests.get(f"{p4.url}/api/me", headers=auth(token), timeout=20).json()
    assert me["user"]["needs_consent"] is True and me["user"]["consent_version"] is None

    refused = requests.post(f"{p4.url}/api/consent", json={"accept_terms": False}, headers=auth(token), timeout=20)
    assert refused.status_code == 422
    accepted = requests.post(f"{p4.url}/api/consent", json={"accept_terms": True}, headers=auth(token), timeout=20)
    assert accepted.status_code == 200 and accepted.json()["user"]["needs_consent"] is False
    assert p4db.users.find_one({"email": email})["consent_version"] == legal.CONSENT_VERSION
    assert requests.get(f"{p4.url}/api/me", headers=auth(token), timeout=20).json()["user"]["needs_consent"] is False


def test_an_older_consent_version_is_asked_again(p4, p4db, cleanup):
    response, email = p4_signup(p4)
    cleanup.append(email)
    p4db.users.update_one({"email": email}, {"$set": {"consent_version": "2020-01-01"}})
    me = requests.get(f"{p4.url}/api/me", headers=auth(response.json()["token"]), timeout=20).json()
    assert me["user"]["needs_consent"] is True


def test_consent_needs_a_signed_in_user(p4):
    assert requests.post(f"{p4.url}/api/consent", json={"accept_terms": True}, timeout=20).status_code == 401


def test_login_does_not_need_consent_in_the_request(p4, cleanup):
    response, email = p4_signup(p4)
    cleanup.append(email)
    login = requests.post(f"{p4.url}/api/auth/login", json={"email": email, "password": "StrongPass123"}, timeout=20)
    assert login.status_code == 200


class TestGoogleFirstUse:
    """A new Google account needs consent; an existing account just signs in."""

    @pytest.fixture
    def fake_google(self, monkeypatch):
        from fastapi.testclient import TestClient
        from motor.motor_asyncio import AsyncIOMotorClient

        def make(email):
            async def verifier(token, client_ids, nonce=None):
                return {"email": email, "email_verified": True, "name": "Gina Google", "iss": "accounts.google.com"}

            monkeypatch.setenv("GOOGLE_CLIENT_IDS", "test-client.apps.googleusercontent.com")
            monkeypatch.setattr(server, "verify_google_id_token", verifier)
            fresh = AsyncIOMotorClient(server.MONGO_URL)
            monkeypatch.setattr(server, "client", fresh)
            monkeypatch.setattr(server, "db", fresh[server.DB_NAME])
            return TestClient(server.app)

        return make

    def test_new_google_user_without_consent_is_refused_and_not_created(self, fake_google, p4db, cleanup):
        email = f"p4.g.{uuid.uuid4().hex[:8]}@example.com"
        cleanup.append(email)
        with fake_google(email) as client:
            refused = client.post("/api/auth/google", json={"id_token": "t" * 30})
            assert refused.status_code == 422 and refused.json()["detail"]["code"] == "consent_required"
            assert p4db.users.find_one({"email": email}) is None
            created = client.post("/api/auth/google", json={"id_token": "t" * 30, "accept_terms": True})
            assert created.status_code == 200 and created.json()["user"]["needs_consent"] is False
        assert p4db.users.find_one({"email": email})["consent_version"] == legal.CONSENT_VERSION

    def test_existing_account_signs_in_without_the_flag(self, fake_google, p4, cleanup):
        response, email = p4_signup(p4)
        cleanup.append(email)
        with fake_google(email) as client:
            again = client.post("/api/auth/google", json={"id_token": "t" * 30})
        assert again.status_code == 200 and again.json()["user"]["email"] == email


class TestAppSide:
    def read(self, *parts):
        return (ROOT / "frontend" / Path(*parts)).read_text(encoding="utf-8")

    def test_signup_screen_requires_the_checkbox(self):
        welcome = self.read("app", "welcome.tsx")
        assert "ConsentCheckbox" in welcome and '(mode === "signup" && !accepted)' in welcome
        assert "accept_terms: acceptTerms" in self.read("src", "context", "auth.tsx")

    def test_consent_screen_is_routed_and_has_both_languages(self):
        assert '"/consent"' in self.read("app", "index.tsx")
        i18n = self.read("src", "i18n.ts")
        for key in ("consentBefore", "consentRequired", "consentTitle", "consentContinue"):
            assert i18n.count(f"    {key}:") == 2, key
