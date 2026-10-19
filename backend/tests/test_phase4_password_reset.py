"""Phase 4 item 4: forgot-password and reset-password (single-use, hashed, 30 minute code; no account enumeration)."""
import re
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

import mailer
import server
from conftest import p4_signup

PASSWORD = "StrongPass123"
NEW_PASSWORD = "BrandNewPass456"


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


def emails_to(p4, address):
    # Signing up also sends a verification email; these tests are about the reset email.
    return [r["body"] for r in p4.email.requests if r["path"] == "/emails" and address in r["body"].get("to", []) and "reset" in r["body"]["subject"]]


def wait_for_email(p4, address, count=1, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        found = emails_to(p4, address)
        if len(found) >= count:
            return found[count - 1]
        time.sleep(0.1)
    raise AssertionError(f"no email to {address}")


def code_in(message):
    return re.search(r"code is: ([A-Z0-9]+)", message["text"]).group(1)


def forgot(p4, email):
    return requests.post(f"{p4.url}/api/auth/forgot-password", json={"email": email}, timeout=20)


def reset(p4, email, code, password=NEW_PASSWORD):
    return requests.post(f"{p4.url}/api/auth/reset-password", json={"email": email, "code": code, "new_password": password}, timeout=20)


def login(p4, email, password):
    return requests.post(f"{p4.url}/api/auth/login", json={"email": email, "password": password}, timeout=20)


_client = None


def mark_verified(email):
    """Password reset only works for verified emails (item 5); these tests are about the reset itself."""
    global _client
    from pymongo import MongoClient

    _client = _client or MongoClient(server.MONGO_URL, serverSelectionTimeoutMS=10000)
    _client[server.DB_NAME].users.update_one({"email": email}, {"$set": {"email_verified": True}})


def new_account(p4, cleanup, verified=True):
    response, email = p4_signup(p4)
    cleanup.append(email)
    if verified:
        mark_verified(email)
    return response.json()["token"], email


def test_forgot_password_sends_a_code_and_reset_changes_the_password(p4, cleanup):
    token, email = new_account(p4, cleanup)
    response = forgot(p4, email)
    assert response.status_code == 200 and response.json()["ok"] is True
    message = wait_for_email(p4, email)
    assert message["from"] == "Wellstride <noreply@wellstride.test>"
    assert "30 minutes" in message["text"] and "wellstride://reset-password" in message["text"]
    assert p4.email.requests[-1]["headers"]["authorization"] == "Bearer re_fake_key_for_tests"

    code = code_in(message)
    assert reset(p4, email, code).status_code == 200
    assert login(p4, email, PASSWORD).status_code == 401, "the old password no longer works"
    assert login(p4, email, NEW_PASSWORD).status_code == 200


def test_the_code_can_be_typed_loosely(p4, cleanup):
    _, email = new_account(p4, cleanup)
    forgot(p4, email)
    code = code_in(wait_for_email(p4, email))
    spaced = f" {code[:4].lower()}-{code[4:].lower()} "
    assert reset(p4, email, spaced).status_code == 200


def test_reset_signs_out_older_tokens(p4, cleanup):
    old_token, email = new_account(p4, cleanup)
    assert requests.get(f"{p4.url}/api/me", headers=auth(old_token), timeout=20).status_code == 200
    time.sleep(1.2)  # token times have one second precision
    forgot(p4, email)
    assert reset(p4, email, code_in(wait_for_email(p4, email))).status_code == 200
    assert requests.get(f"{p4.url}/api/me", headers=auth(old_token), timeout=20).status_code == 401
    fresh = login(p4, email, NEW_PASSWORD).json()["token"]
    assert requests.get(f"{p4.url}/api/me", headers=auth(fresh), timeout=20).status_code == 200


def test_the_code_is_single_use(p4, cleanup):
    _, email = new_account(p4, cleanup)
    forgot(p4, email)
    code = code_in(wait_for_email(p4, email))
    assert reset(p4, email, code).status_code == 200
    second = reset(p4, email, code, "AnotherPass789")
    assert second.status_code == 400 and "invalid or has expired" in second.json()["detail"]
    assert login(p4, email, NEW_PASSWORD).status_code == 200 and login(p4, email, "AnotherPass789").status_code == 401


def test_the_code_expires_after_30_minutes(p4, p4db, cleanup):
    _, email = new_account(p4, cleanup)
    forgot(p4, email)
    code = code_in(wait_for_email(p4, email))
    user = p4db.users.find_one({"email": email})
    record = p4db.password_resets.find_one({"user_id": user["id"]})
    # Created now: the expiry is about 30 minutes ahead (and stored as a date so MongoDB's TTL index can remove it).
    remaining = record["expires_at"].replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    assert timedelta(minutes=29) < remaining <= timedelta(minutes=30)
    p4db.password_resets.update_one({"_id": record["_id"]}, {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}})
    assert reset(p4, email, code).status_code == 400
    assert login(p4, email, PASSWORD).status_code == 200, "an expired code changes nothing"


def test_only_a_hash_is_stored(p4, p4db, cleanup):
    _, email = new_account(p4, cleanup)
    forgot(p4, email)
    code = code_in(wait_for_email(p4, email))
    record = p4db.password_resets.find_one({"user_id": p4db.users.find_one({"email": email})["id"]})
    assert code not in str(record) and record["code_hash"] == server.hash_code(code) and len(record["code_hash"]) == 64


def test_wrong_codes_are_counted_and_the_code_dies_after_five(p4, cleanup):
    _, email = new_account(p4, cleanup)
    forgot(p4, email)
    code = code_in(wait_for_email(p4, email))
    for _ in range(5):
        assert reset(p4, email, "WRONG123").status_code == 400
    assert reset(p4, email, code).status_code == 400, "five wrong guesses cancel the code"
    assert login(p4, email, PASSWORD).status_code == 200


def test_a_new_request_replaces_the_old_code(p4, cleanup):
    _, email = new_account(p4, cleanup)
    forgot(p4, email)
    first = code_in(wait_for_email(p4, email, 1))
    forgot(p4, email)
    second = code_in(wait_for_email(p4, email, 2))
    assert first != second
    assert reset(p4, email, first).status_code == 400
    assert reset(p4, email, second).status_code == 200


def test_no_account_enumeration(p4, cleanup):
    _, email = new_account(p4, cleanup)
    stranger = f"nobody.{uuid.uuid4().hex[:8]}@example.com"
    known, unknown = forgot(p4, email), forgot(p4, stranger)
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    time.sleep(1)
    assert emails_to(p4, stranger) == [], "no email goes to an address with no account"
    # Resetting an unknown address fails exactly like a wrong code.
    wrong = reset(p4, email, "WRONG123")
    nobody = reset(p4, stranger, "WRONG123")
    assert wrong.status_code == nobody.status_code == 400 and wrong.json() == nobody.json()


def test_google_only_accounts_get_no_code(p4, p4db):
    email = f"p4.g.{uuid.uuid4().hex[:8]}@example.com"
    user_id = str(uuid.uuid4())
    p4db.users.insert_one({"id": user_id, "email": email, "name": "G", "password_hash": "", "language": "en", "consent_version": server.legal.CONSENT_VERSION})
    try:
        assert forgot(p4, email).status_code == 200
        time.sleep(1)
        assert emails_to(p4, email) == []
    finally:
        p4db.users.delete_one({"id": user_id})


def test_password_rules_apply_to_the_new_password(p4, cleanup):
    _, email = new_account(p4, cleanup)
    forgot(p4, email)
    code = code_in(wait_for_email(p4, email))
    assert reset(p4, email, code, "short").status_code == 422
    assert reset(p4, email, code).status_code == 200, "a rejected password does not spend the code"


def test_forgot_and_reset_are_rate_limited(p4, cleanup):
    """Each action allows 10 attempts per window per IP and email. Loopback is exempt on the shared test backend, so
    this one gets its own backend with no exemption."""
    from fakes import spawn_backend, stop_backend

    url, proc = spawn_backend({"AUTH_RATE_LIMIT_EXEMPT_IPS": "", "AUTH_RATE_LIMIT": "10", "RESEND_API_KEY": "", "EMAIL_FROM": ""})
    try:
        stranger = f"nobody.{uuid.uuid4().hex[:8]}@example.com"
        codes = [requests.post(f"{url}/api/auth/forgot-password", json={"email": stranger}, timeout=20).status_code for _ in range(11)]
        assert codes[:10] == [200] * 10 and codes[10] == 429
        resets = [requests.post(f"{url}/api/auth/reset-password", json={"email": stranger, "code": "WRONG123", "new_password": NEW_PASSWORD}, timeout=20).status_code for _ in range(11)]
        assert resets[:10] == [400] * 10 and resets[10] == 429
    finally:
        stop_backend(proc)


def test_validation(p4):
    assert requests.post(f"{p4.url}/api/auth/forgot-password", json={"email": "not-an-email"}, timeout=20).status_code == 422
    assert requests.post(f"{p4.url}/api/auth/reset-password", json={"email": "a@example.com", "code": "x", "new_password": NEW_PASSWORD}, timeout=20).status_code == 422


class TestMailer:
    def test_console_is_the_default(self, monkeypatch):
        for name in ("RESEND_API_KEY", "EMAIL_FROM"):
            monkeypatch.delenv(name, raising=False)
        assert isinstance(mailer.get_provider(), mailer.ConsoleEmailProvider)
        monkeypatch.setenv("RESEND_API_KEY", "re_x")
        assert isinstance(mailer.get_provider(), mailer.ConsoleEmailProvider), "both key and sender are needed"

    def test_resend_is_chosen_by_its_settings(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "re_x")
        monkeypatch.setenv("EMAIL_FROM", "Wellstride <hi@example.com>")
        provider = mailer.get_provider()
        assert isinstance(provider, mailer.ResendEmailProvider) and provider.base_url == "https://api.resend.com"

    def test_a_failing_provider_never_raises_to_the_caller(self):
        import asyncio

        class Broken(mailer.EmailProvider):
            name = "broken"

            async def send(self, to, subject, text):
                raise mailer.EmailError("down")

        assert asyncio.run(mailer.send_email("a@example.com", "s", "t", provider=Broken())) is False

    def test_console_logs_the_message(self, caplog):
        import asyncio

        caplog.set_level("INFO", logger="nutrimitra.mailer")
        asyncio.run(mailer.ConsoleEmailProvider().send("a@example.com", "Hello", "code is: ABC"))
        assert "a@example.com" in caplog.text and "ABC" in caplog.text


def test_app_screens_and_strings_exist():
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    for screen in ("forgot-password.tsx", "reset-password.tsx"):
        assert (frontend / "app" / screen).exists(), screen
    assert "forgot-password-link" in (frontend / "app" / "welcome.tsx").read_text(encoding="utf-8")
    i18n = (frontend / "src" / "i18n.ts").read_text(encoding="utf-8")
    for key in ("forgotPassword", "forgotTitle", "sendCode", "resetTitle", "resetCode", "newPassword", "resetButton", "resetDone"):
        assert i18n.count(f"    {key}:") == 2, key
