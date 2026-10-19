"""Phase 3 item 6: Google sign-in with Google's own OAuth (ID token verified by the backend).

The integration tests use real signature verification: tokens are signed with a throwaway RSA key and the
backend fetches the matching certificate from a local fake of Google's certificate endpoint
(GOOGLE_CERTS_URL), so nothing here needs Google credentials."""
import datetime as dt
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import jwt
import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pymongo import MongoClient

import server
from fakes import spawn_backend, stop_backend

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"

CLIENT_A = "client-a.apps.googleusercontent.com"
CLIENT_B = "client-b.apps.googleusercontent.com"
ISSUER = "https://accounts.google.com"
KID = "test-key-1"
ROOT = Path(server.__file__).parent.parent


def make_key_and_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fake-google")])
    now = dt.datetime.now(dt.timezone.utc)
    cert = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1)).not_valid_after(now + dt.timedelta(days=30)).sign(key, hashes.SHA256())
    pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return key, pem


SIGNING_KEY, SIGNING_CERT = make_key_and_cert()
OTHER_KEY, _ = make_key_and_cert()


def id_token(email, aud=CLIENT_A, iss=ISSUER, exp_in=3600, key=SIGNING_KEY, **extra):
    now = int(time.time())
    claims = {"iss": iss, "aud": aud, "sub": uuid.uuid4().hex, "iat": now, "exp": now + exp_in, "email": email, "email_verified": True, "name": "Asha Rao", "picture": "https://example.com/a.png"}
    claims.update(extra)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": KID})


class CertsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({KID: SIGNING_CERT}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def certs_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), CertsHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture(scope="module")
def backend(certs_server):
    url, proc = spawn_backend({"GOOGLE_CLIENT_IDS": f"{CLIENT_A}, {CLIENT_B}", "GOOGLE_CERTS_URL": certs_server})
    yield url
    stop_backend(proc)


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=10000)
    yield client.test_database
    client.close()


@pytest.fixture
def cleanup(mongo):
    emails = []
    yield emails
    for email in emails:
        user = mongo.users.find_one({"email": email})
        if user:
            mongo.profiles.delete_many({"user_id": user["id"]})
            mongo.users.delete_many({"id": user["id"]})


def new_email(prefix="g"):
    return f"{prefix}.{uuid.uuid4().hex[:10]}@example.com"


def google(url, token, **extra):
    return requests.post(f"{url}/api/auth/google", json={"id_token": token, **extra}, timeout=30)


class TestGoogleSignIn:
    def test_valid_token_creates_an_account_and_signs_in(self, backend, mongo, cleanup):
        email = new_email("New.Person")
        cleanup.append(email.lower())
        resp = google(backend, id_token(email))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["user"]["email"] == email.lower() and body["user"]["name"] == "Asha Rao"
        assert body["user"]["onboarding_complete"] is False
        stored = mongo.users.find_one({"email": email.lower()})
        assert stored["password_hash"] == "" and stored["picture"] == "https://example.com/a.png"
        me = requests.get(f"{backend}/api/me", headers={"Authorization": f"Bearer {body['token']}"}, timeout=20)
        assert me.status_code == 200 and me.json()["user"]["id"] == body["user"]["id"]

    def test_either_configured_client_id_is_accepted(self, backend, cleanup):
        email = new_email()
        cleanup.append(email)
        assert google(backend, id_token(email, aud=CLIENT_B)).status_code == 200

    def test_existing_google_created_account_is_matched_by_email(self, backend, mongo, cleanup):
        """Accounts created by the old Emergent flow have an empty password hash and keep working."""
        email = new_email("legacy")
        cleanup.append(email)
        user_id = str(uuid.uuid4())
        mongo.users.insert_one({"id": user_id, "email": email, "name": "Legacy Google", "picture": "", "password_hash": "", "language": "te", "onboarding_complete": True, "created_at": "2026-09-01T00:00:00+00:00"})
        body = google(backend, id_token(email.upper())).json()
        assert body["user"]["id"] == user_id and body["user"]["onboarding_complete"] is True
        assert mongo.users.count_documents({"email": email}) == 1, "no duplicate account"

    def test_email_account_with_the_same_verified_email_is_the_same_account(self, backend, cleanup):
        email = new_email("both")
        cleanup.append(email)
        signup = requests.post(f"{backend}/api/auth/signup", json={"email": email, "password": "StrongPass123"}, timeout=20).json()
        assert google(backend, id_token(email)).json()["user"]["id"] == signup["user"]["id"]
        # ...and the password still works afterwards
        assert requests.post(f"{backend}/api/auth/login", json={"email": email, "password": "StrongPass123"}, timeout=20).status_code == 200

    def test_repeated_google_sign_ins_reuse_one_account(self, backend, mongo, cleanup):
        email = new_email("again")
        cleanup.append(email)
        ids = {google(backend, id_token(email)).json()["user"]["id"] for _ in range(3)}
        assert len(ids) == 1 and mongo.users.count_documents({"email": email}) == 1

    @pytest.mark.parametrize("label,overrides", [
        ("wrong audience", {"aud": "someone-else.apps.googleusercontent.com"}),
        ("expired", {"exp_in": -3600}),
        ("wrong issuer", {"iss": "https://evil.example.com"}),
        ("signed by another key", {"key": OTHER_KEY}),
        ("email not verified", {"email_verified": False}),
    ])
    def test_bad_tokens_are_rejected(self, backend, mongo, label, overrides):
        email = new_email("bad")
        resp = google(backend, id_token(email, **overrides))
        assert resp.status_code == 401, (label, resp.text)
        assert resp.json()["detail"] == "Google sign-in could not be verified"
        assert mongo.users.count_documents({"email": email}) == 0, "no account is created from a rejected token"

    def test_token_without_an_email_is_rejected(self, backend):
        assert google(backend, id_token(None)).status_code == 401

    def test_garbage_and_short_tokens(self, backend):
        assert google(backend, "this-is-not-a-jwt-at-all-1234").status_code == 401
        assert requests.post(f"{backend}/api/auth/google", json={"id_token": "short"}, timeout=20).status_code == 422
        assert requests.post(f"{backend}/api/auth/google", json={}, timeout=20).status_code == 422

    def test_nonce_must_match_when_sent(self, backend, cleanup):
        email = new_email("nonce")
        cleanup.append(email)
        token = id_token(email, nonce="abc123")
        assert google(backend, token, nonce="abc123").status_code == 200
        assert google(backend, token, nonce="different").status_code == 401
        assert google(backend, id_token(email), nonce="abc123").status_code == 401, "a token without the nonce is refused"


class TestGoogleOff:
    def test_without_client_ids_the_endpoint_says_so_and_email_login_works(self):
        url, proc = spawn_backend({"GOOGLE_CLIENT_IDS": "", "GOOGLE_CLIENT_ID": ""})
        try:
            resp = google(url, "a" * 40)
            assert resp.status_code == 503, resp.text
            assert resp.json()["detail"]["code"] == "google_not_configured"
            assert "email and password" in resp.json()["detail"]["message"]
            email = new_email("plain")
            signup = requests.post(f"{url}/api/auth/signup", json={"email": email, "password": "StrongPass123"}, timeout=20)
            assert signup.status_code == 200
            assert requests.post(f"{url}/api/auth/login", json={"email": email, "password": "StrongPass123"}, timeout=20).status_code == 200
            MongoClient("mongodb://127.0.0.1:27017").test_database.users.delete_many({"email": email})
        finally:
            stop_backend(proc)

    def test_single_client_id_variable_also_works(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_IDS", raising=False)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", " one.apps.googleusercontent.com ")
        assert server.google_client_ids() == ["one.apps.googleusercontent.com"]
        monkeypatch.setenv("GOOGLE_CLIENT_IDS", "a.apps.googleusercontent.com, b.apps.googleusercontent.com,")
        assert server.google_client_ids() == ["a.apps.googleusercontent.com", "b.apps.googleusercontent.com"]
        monkeypatch.delenv("GOOGLE_CLIENT_IDS")
        monkeypatch.delenv("GOOGLE_CLIENT_ID")
        assert server.google_client_ids() == []


class TestGoogleRateLimit:
    def test_attempts_are_limited_per_ip(self, certs_server):
        url, proc = spawn_backend({"GOOGLE_CLIENT_IDS": CLIENT_A, "GOOGLE_CERTS_URL": certs_server, "AUTH_RATE_LIMIT_EXEMPT_IPS": "", "TRUST_PROXY_HEADERS": "1"})
        try:
            ip = {"X-Forwarded-For": "203.0.113.77"}
            codes = [requests.post(f"{url}/api/auth/google", json={"id_token": "x" * 40}, headers=ip, timeout=20).status_code for _ in range(11)]
            assert codes == [401] * 10 + [429]
            other = requests.post(f"{url}/api/auth/google", json={"id_token": "x" * 40}, headers={"X-Forwarded-For": "198.51.100.5"}, timeout=20)
            assert other.status_code == 401
        finally:
            stop_backend(proc)


class TestFakeVerifier:
    """The verifier is one replaceable function, so the endpoint's account logic can be tested without any tokens."""

    def test_endpoint_uses_the_replaceable_verifier(self, monkeypatch, mongo, cleanup):
        from fastapi.testclient import TestClient

        email = new_email("fakeverifier")
        cleanup.append(email)
        seen = {}

        async def fake_verifier(token, client_ids, nonce=None):
            seen.update(token=token, client_ids=client_ids, nonce=nonce)
            return {"email": email.upper(), "email_verified": True, "name": "fake person"}

        monkeypatch.setenv("GOOGLE_CLIENT_IDS", CLIENT_A)
        monkeypatch.setattr(server, "verify_google_id_token", fake_verifier)
        # A Mongo client of its own: motor clients are tied to the event loop they are first used in.
        from motor.motor_asyncio import AsyncIOMotorClient

        fresh_client = AsyncIOMotorClient(server.MONGO_URL)
        monkeypatch.setattr(server, "client", fresh_client)
        monkeypatch.setattr(server, "db", fresh_client[server.DB_NAME])
        with TestClient(server.app) as client:
            body = client.post("/api/auth/google", json={"id_token": "t" * 30, "nonce": "n1"}).json()
        assert body["user"]["email"] == email and body["user"]["name"] == "Fake Person"
        assert seen == {"token": "t" * 30, "client_ids": [CLIENT_A], "nonce": "n1"}


class TestEmergentGoogleRemoved:
    def test_old_endpoint_and_settings_are_gone(self, backend):
        assert requests.post(f"{backend}/api/auth/session", json={"session_id": "abcdefgh"}, timeout=20).status_code in {404, 405}
        for path in ("backend/server.py", "backend/.env.example", "frontend/src/context/auth.tsx", "README.md"):
            text = (ROOT / path).read_text(encoding="utf-8")
            for needle in ("emergentagent", "GOOGLE_AUTH_HANDOFF_URL", "EXPO_PUBLIC_GOOGLE_AUTH_URL", "session_id"):
                assert needle not in text, (path, needle)

    def test_env_example_documents_google_settings(self):
        text = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
        assert "GOOGLE_CLIENT_IDS=\n" in text and "GOOGLE_CERTS_URL" in text

    def test_google_is_a_declared_dependency(self):
        assert "google-auth" in (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8")


class TestAppWiring:
    """The app has no UI test harness, so check the source: the button is gated on config, and sign-in uses the new endpoint."""

    def read(self, *parts):
        return ROOT.joinpath("frontend", *parts).read_text(encoding="utf-8")

    def test_google_is_off_without_a_client_id(self):
        google_auth = self.read("src", "lib", "google-auth.ts")
        assert 'process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID || ""' in google_auth
        assert "export const googleEnabled = GOOGLE_CLIENT_ID.length > 0" in google_auth
        assert "if (!googleEnabled || !request) return null" in google_auth
        welcome = self.read("app", "welcome.tsx")
        assert "{googleEnabled ? <Button testID=\"google-signin-button\"" in welcome

    def test_sign_in_uses_the_new_endpoint_and_a_nonce(self):
        auth = self.read("src", "context", "auth.tsx")
        assert '"/auth/google", { id_token: result.idToken, nonce: result.nonce }' in auth
        assert "Linking" not in auth and "WebBrowser" not in auth
        google_auth = self.read("src", "lib", "google-auth.ts")
        assert "ResponseType.IdToken" in google_auth and "extraParams: { nonce }" in google_auth
        assert "https://accounts.google.com" in google_auth

    def test_error_text_is_translated(self):
        english, telugu = self.read("src", "i18n.ts").split("  te: {", 1)
        assert "googleFailed:" in english and "googleFailed:" in telugu
        assert "t.googleFailed" in self.read("app", "welcome.tsx")

    def test_env_examples_and_readme(self):
        assert "EXPO_PUBLIC_GOOGLE_CLIENT_ID=\n" in self.read(".env.example")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "GOOGLE_CLIENT_IDS" in readme and "EXPO_PUBLIC_GOOGLE_CLIENT_ID" in readme and "Web application" in readme
        assert {"expo-auth-session", "expo-crypto"} <= set(json.loads(self.read("package.json"))["dependencies"])


ORIGINAL_DATABASE = (server.client, server.db)


class TestIsolation:
    """Regression: Phase 2 tests swap server.db for a scratch client and close it; an in-process test that ran
    afterwards (the Google fake verifier) failed with "Event loop is closed", but only in a full run.
    These two run in order: the first replaces the database, the second checks the conftest fixture put it back."""

    def test_a_replaces_the_database(self):
        server.client, server.db = object(), object()

    def test_b_the_original_database_is_back(self):
        assert (server.client, server.db) == ORIGINAL_DATABASE
