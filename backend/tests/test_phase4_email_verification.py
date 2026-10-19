"""Phase 4 item 5: email verification codes. Unverified users can use the app; password reset needs a verified email."""
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

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


def emails_to(p4, address, subject_part="verification"):
    return [r["body"] for r in p4.email.requests if r["path"] == "/emails" and address in r["body"].get("to", []) and subject_part in r["body"]["subject"]]


def wait_for_email(p4, address, count=1, seconds=10, subject_part="verification"):
    deadline = time.time() + seconds
    while time.time() < deadline:
        found = emails_to(p4, address, subject_part)
        if len(found) >= count:
            return found[count - 1]
        time.sleep(0.1)
    raise AssertionError(f"no email to {address}")


def code_in(message):
    return re.search(r"code is: (\d{6})", message["text"]).group(1)


def verify(p4, token, code):
    return requests.post(f"{p4.url}/api/auth/verify-email", json={"code": code}, headers=auth(token), timeout=20)


def resend(p4, token):
    return requests.post(f"{p4.url}/api/auth/resend-verification", headers=auth(token), timeout=20)


def me(p4, token):
    return requests.get(f"{p4.url}/api/me", headers=auth(token), timeout=20).json()["user"]


def new_account(p4, cleanup):
    response, email = p4_signup(p4)
    cleanup.append(email)
    return response.json(), email


def test_signup_sends_a_code_and_the_user_starts_unverified(p4, cleanup):
    body, email = new_account(p4, cleanup)
    assert body["user"]["email_verified"] is False
    message = wait_for_email(p4, email)
    assert re.fullmatch(r"\d{6}", code_in(message)) and "60 minutes" in message["text"]
    # Unverified users can use the app.
    assert me(p4, body["token"])["email_verified"] is False
    assert requests.get(f"{p4.url}/api/dashboard", headers=auth(body["token"]), timeout=20).status_code == 200


def test_the_right_code_verifies_and_is_single_use(p4, cleanup):
    body, email = new_account(p4, cleanup)
    code = code_in(wait_for_email(p4, email))
    response = verify(p4, body["token"], code)
    assert response.status_code == 200 and response.json()["user"]["email_verified"] is True
    assert me(p4, body["token"])["email_verified"] is True
    # Already verified: a repeat is harmless.
    assert verify(p4, body["token"], code).status_code == 200


def test_wrong_codes_are_refused_and_five_cancel_the_code(p4, cleanup):
    body, email = new_account(p4, cleanup)
    code = code_in(wait_for_email(p4, email))
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert verify(p4, body["token"], wrong).status_code == 400
    assert verify(p4, body["token"], code).status_code == 400, "the code was cancelled; ask for a new one"
    assert me(p4, body["token"])["email_verified"] is False
    assert resend(p4, body["token"]).json() == {"ok": True, "already_verified": False}
    fresh = code_in(wait_for_email(p4, email, 2))
    assert verify(p4, body["token"], fresh).status_code == 200


def test_the_code_expires(p4, p4db, cleanup):
    body, email = new_account(p4, cleanup)
    code = code_in(wait_for_email(p4, email))
    record = p4db.email_verifications.find_one({"user_id": body["user"]["id"]})
    remaining = record["expires_at"].replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    assert timedelta(minutes=59) < remaining <= timedelta(minutes=60)
    assert code not in str(record), "only a hash is stored"
    p4db.email_verifications.update_one({"_id": record["_id"]}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}})
    assert verify(p4, body["token"], code).status_code == 400


def test_resend_replaces_the_code(p4, cleanup):
    body, email = new_account(p4, cleanup)
    first = code_in(wait_for_email(p4, email))
    assert resend(p4, body["token"]).status_code == 200
    second = code_in(wait_for_email(p4, email, 2))
    if first != second:
        assert verify(p4, body["token"], first).status_code == 400
    assert verify(p4, body["token"], second).status_code == 200
    assert resend(p4, body["token"]).json() == {"ok": True, "already_verified": True}


def test_verification_needs_sign_in(p4):
    assert requests.post(f"{p4.url}/api/auth/verify-email", json={"code": "123456"}, timeout=20).status_code == 401
    assert requests.post(f"{p4.url}/api/auth/resend-verification", timeout=20).status_code == 401


def test_password_reset_only_works_for_verified_emails(p4, cleanup):
    body, email = new_account(p4, cleanup)
    wait_for_email(p4, email)
    before = len(emails_to(p4, email, "reset"))
    response = requests.post(f"{p4.url}/api/auth/forgot-password", json={"email": email}, timeout=20)
    assert response.status_code == 200 and response.json()["ok"] is True, "same answer as for any other address"
    time.sleep(1)
    assert len(emails_to(p4, email, "reset")) == before, "no reset email goes to an unverified address"

    assert verify(p4, body["token"], code_in(wait_for_email(p4, email))).status_code == 200
    requests.post(f"{p4.url}/api/auth/forgot-password", json={"email": email}, timeout=20)
    assert wait_for_email(p4, email, 1, subject_part="reset")


def test_google_accounts_count_as_verified(p4, p4db):
    from fastapi.testclient import TestClient
    from motor.motor_asyncio import AsyncIOMotorClient

    email = f"p4.g.{uuid.uuid4().hex[:8]}@example.com"

    async def verifier(token, client_ids, nonce=None):
        return {"email": email, "email_verified": True, "name": "Gina Google", "iss": "accounts.google.com"}

    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("GOOGLE_CLIENT_IDS", "test-client.apps.googleusercontent.com")
        mp.setattr(server, "verify_google_id_token", verifier)
        fresh = AsyncIOMotorClient(server.MONGO_URL)
        mp.setattr(server, "client", fresh)
        mp.setattr(server, "db", fresh[server.DB_NAME])
        with TestClient(server.app) as client:
            created = client.post("/api/auth/google", json={"id_token": "t" * 30, "accept_terms": True}).json()
        assert created["user"]["email_verified"] is True
        assert p4db.users.find_one({"email": email})["email_verified"] is True
    finally:
        mp.undo()
        user = p4db.users.find_one({"email": email})
        if user:
            p4db.users.delete_one({"id": user["id"]})


def test_older_accounts_with_a_password_are_unverified_until_they_verify(p4, p4db, cleanup):
    body, email = new_account(p4, cleanup)
    p4db.users.update_one({"email": email}, {"$unset": {"email_verified": ""}})
    assert me(p4, body["token"])["email_verified"] is False
    assert resend(p4, body["token"]).json()["already_verified"] is False


def test_resend_is_rate_limited():
    from fakes import spawn_backend, stop_backend
    from pymongo import MongoClient

    url, proc = spawn_backend({"AUTH_RATE_LIMIT_EXEMPT_IPS": "", "AUTH_RATE_LIMIT": "10", "RESEND_API_KEY": "", "EMAIL_FROM": ""})
    email = f"p4.rl.{uuid.uuid4().hex[:8]}@example.com"
    try:
        token = requests.post(f"{url}/api/auth/signup", json={"email": email, "password": "StrongPass123", "accept_terms": True}, timeout=20).json()["token"]
        codes = [requests.post(f"{url}/api/auth/resend-verification", headers=auth(token), timeout=20).status_code for _ in range(11)]
        assert codes[:10] == [200] * 10 and codes[10] == 429
    finally:
        stop_backend(proc)
        db = MongoClient(server.MONGO_URL)[server.DB_NAME]
        user = db.users.find_one({"email": email})
        if user:
            for name in db.list_collection_names():
                db[name].delete_many({"user_id": user["id"]})
            db.users.delete_one({"id": user["id"]})


def test_app_has_the_banner_and_screen_in_both_languages():
    frontend = ROOT / "frontend"
    assert "verify-banner" in (frontend / "app" / "(tabs)" / "index.tsx").read_text(encoding="utf-8")
    assert (frontend / "app" / "verify-email.tsx").exists()
    i18n = (frontend / "src" / "i18n.ts").read_text(encoding="utf-8")
    for key in ("verifyBannerTitle", "verifyBannerSub", "verifyTitle", "verifySub", "verifyCode", "verifyButton", "verifyResend", "verifySent", "verifyDone"):
        assert i18n.count(f"    {key}:") == 2, key
