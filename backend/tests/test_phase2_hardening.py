"""Phase 2 backend-hardening regression tests.

Same approach as test_phase1_fixes.py: integration tests against the live server
(EXPO_PUBLIC_BACKEND_URL) and the same MongoDB (test_database), with a fresh throwaway
user per module run. Pure helpers are unit-tested by importing server directly.
"""
import asyncio
import json
import os
import threading
import socket
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
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

USER_COLLECTIONS = ("plans", "meals", "activities", "weights", "coach_messages", "profiles", "permissions", "reminders", "health_records", "user_sessions")


def unique_email(prefix="phase2"):
    return f"{prefix}.{uuid.uuid4().hex[:10]}@example.com"


def remove_user(mongo, user_id):
    for name in USER_COLLECTIONS:
        mongo[name].delete_many({"user_id": user_id})
    mongo.users.delete_many({"id": user_id})


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def spawn_backend(**env_overrides):
    """Start a second backend on the same database with extra environment; returns (url, process)."""
    port = free_port()
    env = {**os.environ, **env_overrides}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)], cwd=Path(server.__file__).parent, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            if requests.get(f"{url}/api/", timeout=1).status_code == 200:
                return url, proc
        except requests.RequestException:
            time.sleep(0.5)
    proc.terminate()
    pytest.fail("extra backend did not start")


def stop_backend(proc):
    proc.terminate()
    proc.wait(timeout=20)


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
    email = unique_email()
    resp = s.post(f"{BASE_URL}/api/auth/signup", json={"email": email, "password": "StrongPass123", "name": "Phase Two"}, timeout=20)
    assert resp.status_code == 200, resp.text
    s.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    s.user_id = resp.json()["user"]["id"]
    s.email = email
    resp = s.put(f"{BASE_URL}/api/profile", json=PROFILE, timeout=20)
    assert resp.status_code == 200, resp.text
    yield s
    remove_user(mongo, s.user_id)


class TestIndexes:
    """Item 1: indexes are created at startup, emails are unique, and expired sessions are dropped."""

    def test_startup_created_indexes(self, mongo):
        users = mongo.users.index_information()
        assert users["email_unique"]["unique"] is True
        assert users["email_unique"]["key"] == [("email", 1)]
        assert ("user_date" in mongo.meals.index_information()) and ("user_created" in mongo.meals.index_information())
        assert mongo.meals.index_information()["user_date"]["key"] == [("user_id", 1), ("date", 1)]
        for collection in ("activities", "weights", "coach_messages"):
            assert "user_created" in mongo[collection].index_information(), collection
        assert "user_updated" in mongo.plans.index_information()
        assert "user_start" in mongo.health_records.index_information()
        ttl = mongo.user_sessions.index_information()["expires_ttl"]
        assert ttl["expireAfterSeconds"] == 0 and ttl["key"] == [("expires_at", 1)]

    def test_ensure_indexes_is_idempotent(self, mongo):
        before = {name: mongo[name].index_information() for name in ("users", "meals", "user_sessions")}

        async def twice():
            server.client = AsyncIOMotorClient(server.MONGO_URL)
            server.db = server.client[DB_NAME]
            await server.ensure_indexes()
            await server.ensure_indexes()
            server.client.close()

        asyncio.run(twice())
        assert {name: mongo[name].index_information() for name in ("users", "meals", "user_sessions")} == before

    def test_duplicate_emails_fall_back_without_deleting(self):
        """Existing duplicates are reported and kept; a non-unique index is created instead."""
        scratch = f"phase2_dupes_{uuid.uuid4().hex[:8]}"
        sync = MongoClient(MONGO_URL)
        sync[scratch].users.insert_many([{"id": "a", "email": "same@example.com"}, {"id": "b", "email": "same@example.com"}])

        async def run():
            server.client = AsyncIOMotorClient(server.MONGO_URL)
            server.db = server.client[scratch]
            try:
                return await server.ensure_email_index()
            finally:
                server.client.close()

        try:
            assert asyncio.run(run()) is False
            assert sync[scratch].users.count_documents({"email": "same@example.com"}) == 2
            info = sync[scratch].users.index_information()
            assert "email" in info and not info["email"].get("unique")
        finally:
            sync.drop_database(scratch)
            sync.close()

    def test_legacy_string_expiry_is_migrated_to_dates(self):
        scratch = f"phase2_sessions_{uuid.uuid4().hex[:8]}"
        sync = MongoClient(MONGO_URL)
        future = datetime.now(timezone.utc) + timedelta(days=2)
        sync[scratch].user_sessions.insert_many([
            {"session_token": "s1", "user_id": "u", "expires_at": future.isoformat()},
            {"session_token": "s2", "user_id": "u", "expires_at": "not a date"},
        ])

        async def run():
            server.client = AsyncIOMotorClient(server.MONGO_URL)
            server.db = server.client[scratch]
            try:
                return await server.migrate_session_expiry()
            finally:
                server.client.close()

        try:
            assert asyncio.run(run()) == 1
            migrated = sync[scratch].user_sessions.find_one({"session_token": "s1"})
            assert isinstance(migrated["expires_at"], datetime)
            assert abs(migrated["expires_at"].replace(tzinfo=timezone.utc) - future) < timedelta(seconds=1)
            assert sync[scratch].user_sessions.find_one({"session_token": "s2"})["expires_at"] == "not a date", "unparseable values are left alone"
        finally:
            sync.drop_database(scratch)
            sync.close()

    def test_concurrent_signups_with_same_email_yield_one_account(self, mongo):
        email = unique_email("race")

        def signup(_):
            return requests.post(f"{BASE_URL}/api/auth/signup", json={"email": email, "password": "StrongPass123"}, timeout=30).status_code

        with ThreadPoolExecutor(max_workers=6) as pool:
            codes = list(pool.map(signup, range(6)))
        try:
            assert codes.count(200) == 1, codes
            assert set(codes) <= {200, 409}, codes
            assert mongo.users.count_documents({"email": email}) == 1
        finally:
            for user in mongo.users.find({"email": email}):
                remove_user(mongo, user["id"])

    def test_email_is_case_insensitive(self, mongo):
        email = unique_email("Case.Mixed")
        resp = requests.post(f"{BASE_URL}/api/auth/signup", json={"email": email, "password": "StrongPass123"}, timeout=20)
        assert resp.status_code == 200, resp.text
        user_id = resp.json()["user"]["id"]
        try:
            assert resp.json()["user"]["email"] == email.lower()
            assert requests.post(f"{BASE_URL}/api/auth/signup", json={"email": email.upper(), "password": "StrongPass123"}, timeout=20).status_code == 409
            assert requests.post(f"{BASE_URL}/api/auth/login", json={"email": email.lower(), "password": "StrongPass123"}, timeout=20).status_code == 200
        finally:
            remove_user(mongo, user_id)

    def test_session_expiry_dates(self, fresh, mongo):
        """Sessions use BSON dates (so the TTL index applies); expired ones are rejected even before TTL cleanup."""
        now = datetime.now(timezone.utc)
        tokens = {"valid": uuid.uuid4().hex, "expired": uuid.uuid4().hex, "legacy": uuid.uuid4().hex}
        mongo.user_sessions.insert_many([
            {"session_token": tokens["valid"], "user_id": fresh.user_id, "expires_at": now + timedelta(days=1), "created_at": now.isoformat()},
            {"session_token": tokens["expired"], "user_id": fresh.user_id, "expires_at": now - timedelta(minutes=5), "created_at": now.isoformat()},
            {"session_token": tokens["legacy"], "user_id": fresh.user_id, "expires_at": (now + timedelta(days=1)).isoformat(), "created_at": now.isoformat()},
        ])
        try:
            def me(token):
                return requests.get(f"{BASE_URL}/api/me", headers={"Authorization": f"Bearer {token}"}, timeout=20).status_code

            assert me(tokens["valid"]) == 200
            assert me(tokens["expired"]) == 401
            assert me(tokens["legacy"]) == 200, "legacy string expiry must keep working until migrated"
        finally:
            mongo.user_sessions.delete_many({"user_id": fresh.user_id})

    def test_parse_expiry(self):
        aware = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
        assert server.parse_expiry(aware) == aware
        assert server.parse_expiry(datetime(2026, 10, 1, 12)) == aware
        assert server.parse_expiry("2026-10-01T12:00:00+00:00") == aware
        assert server.parse_expiry("2026-10-01T12:00:00Z") == aware
        assert server.parse_expiry("garbage") is None
        assert server.parse_expiry(None) is None


@pytest.fixture(scope="module")
def limited_backend():
    """A backend with no loopback exemption that trusts X-Forwarded-For, so tests can act as different clients."""
    url, proc = spawn_backend(AUTH_RATE_LIMIT="10", AUTH_RATE_WINDOW_MINUTES="15", AUTH_RATE_LIMIT_EXEMPT_IPS="", TRUST_PROXY_HEADERS="1")
    yield url
    stop_backend(proc)


def login(url, email, password="WrongPass123", ip="203.0.113.1"):
    return requests.post(f"{url}/api/auth/login", json={"email": email, "password": password}, headers={"X-Forwarded-For": ip}, timeout=20)


class TestAuthRateLimit:
    """Item 2: /auth/login and /auth/signup allow 10 attempts per 15 minutes per IP and per email."""

    def test_limiter_window(self):
        now = [1000.0]
        limiter = server.SlidingWindowLimiter(3, 60, clock=lambda: now[0])
        assert [limiter.record("k") for _ in range(3)] == [None, None, None]
        assert limiter.record("k") == 60
        now[0] += 30
        assert limiter.record("k") == 30, "over-limit attempts are not counted, so the wait shrinks"
        assert limiter.record("other") is None
        now[0] += 31
        assert limiter.record("k") is None, "the oldest attempts aged out of the window"
        limiter.reset("k")
        assert limiter.attempts.get("k") is None

    def test_per_ip_login_limit(self, limited_backend):
        ip = f"203.0.113.{uuid.uuid4().int % 200 + 1}"
        codes = [login(limited_backend, unique_email("nobody"), ip=ip).status_code for _ in range(10)]
        assert codes == [401] * 10
        blocked = login(limited_backend, unique_email("nobody"), ip=ip)
        assert blocked.status_code == 429, blocked.text
        assert "Too many attempts" in blocked.json()["detail"] and "15 minutes" in blocked.json()["detail"]
        assert 0 < int(blocked.headers["Retry-After"]) <= 900
        assert login(limited_backend, unique_email("nobody"), ip="198.51.100.7").status_code == 401, "other clients are unaffected"

    def test_per_email_login_limit_across_ips(self, limited_backend):
        email = unique_email("target")
        codes = [login(limited_backend, email, ip=f"192.0.2.{n}").status_code for n in range(1, 11)]
        assert codes == [401] * 10
        assert login(limited_backend, email, ip="192.0.2.99").status_code == 429

    def test_successful_login_resets_the_email_counter(self, limited_backend, fresh):
        for n in range(9):
            assert login(limited_backend, fresh.email, ip=f"198.18.0.{n + 1}").status_code == 401
        assert login(limited_backend, fresh.email, password="StrongPass123", ip="198.18.1.1").status_code == 200
        for n in range(5):
            assert login(limited_backend, fresh.email, ip=f"198.18.2.{n + 1}").status_code == 401, "counter was reset by the success"

    def test_signup_limit_per_ip(self, limited_backend, mongo):
        ip = "203.0.113.250"
        emails = [unique_email("spam") for _ in range(11)]
        try:
            codes = [requests.post(f"{limited_backend}/api/auth/signup", json={"email": e, "password": "StrongPass123"}, headers={"X-Forwarded-For": ip}, timeout=20).status_code for e in emails]
            assert codes == [200] * 10 + [429], codes
        finally:
            for user in mongo.users.find({"email": {"$in": emails}}):
                remove_user(mongo, user["id"])

    def test_local_and_test_suite_logins_are_exempt(self):
        """The dev server exempts loopback by default, so the suite's many logins are never blocked."""
        email = unique_email("loopback")
        codes = [requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "WrongPass123"}, timeout=20).status_code for _ in range(12)]
        assert codes == [401] * 12


def preflight(url, origin, method="POST"):
    return requests.options(f"{url}/api/auth/login", headers={"Origin": origin, "Access-Control-Request-Method": method, "Access-Control-Request-Headers": "authorization,content-type"}, timeout=20)


class TestCors:
    """Item 3: CORS allows only CORS_ORIGINS; the default covers the local Expo web build."""

    def test_parse_origins(self):
        assert server.parse_origins(" https://a.example.com/, http://localhost:8081 ,,") == ["https://a.example.com", "http://localhost:8081"]

    @pytest.mark.parametrize("origin", ["http://localhost:8081", "http://localhost:19006"])
    def test_default_allows_expo_web(self, origin):
        resp = preflight(BASE_URL, origin)
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("access-control-allow-origin") == origin
        assert "authorization" in resp.headers.get("access-control-allow-headers", "").lower()
        simple = requests.get(f"{BASE_URL}/api/", headers={"Origin": origin}, timeout=20)
        assert simple.headers.get("access-control-allow-origin") == origin

    def test_default_rejects_other_origins(self):
        resp = preflight(BASE_URL, "https://evil.example.com")
        assert resp.status_code == 400
        assert "access-control-allow-origin" not in resp.headers
        simple = requests.get(f"{BASE_URL}/api/", headers={"Origin": "https://evil.example.com"}, timeout=20)
        assert "access-control-allow-origin" not in simple.headers
        assert simple.headers.get("access-control-allow-credentials") is None

    def test_env_allowlist_replaces_defaults(self):
        url, proc = spawn_backend(CORS_ORIGINS="https://app.example.com, https://admin.example.com/")
        try:
            assert preflight(url, "https://app.example.com").headers.get("access-control-allow-origin") == "https://app.example.com"
            assert preflight(url, "https://admin.example.com").headers.get("access-control-allow-origin") == "https://admin.example.com"
            assert preflight(url, "http://localhost:8081").status_code == 400, "an explicit list replaces the local defaults"
        finally:
            stop_backend(proc)


class TestLifespan:
    """Item 4: startup/shutdown run through a lifespan handler, not the deprecated @app.on_event."""

    def test_no_on_event_handlers(self):
        assert server.app.router.on_startup == [] and server.app.router.on_shutdown == []
        assert "on_event" not in Path(server.__file__).read_text(encoding="utf-8")

    def test_lifespan_runs_startup_and_shutdown(self, monkeypatch):
        from fastapi.testclient import TestClient

        calls = []

        async def fake_ensure_indexes():
            calls.append("indexes")

        class FakeClient:
            def close(self):
                calls.append("closed")

        monkeypatch.setattr(server, "ensure_indexes", fake_ensure_indexes)
        monkeypatch.setattr(server, "client", FakeClient())
        with TestClient(server.app) as test_client:
            assert calls == ["indexes"], "indexes are ensured before the first request"
            assert test_client.get("/api/").status_code == 200
        assert calls == ["indexes", "closed"], "the Mongo client is closed on shutdown"

    def test_server_logs_startup_through_lifespan(self):
        """A real server process starts, serves, and shuts down cleanly with the lifespan handler."""
        url, proc = spawn_backend()
        try:
            assert requests.get(f"{url}/api/", timeout=10).status_code == 200
        finally:
            stop_backend(proc)
        assert proc.returncode is not None


class TestPlanCap:
    """Item 6: only the latest 5 plans per user are kept; the plan just created is never deleted."""

    @staticmethod
    def old_plans(user_id, count):
        base = datetime.now(timezone.utc) - timedelta(days=30)
        return [{"user_id": user_id, "goal": "x", "days": [], "updated_at": (base + timedelta(days=n)).isoformat(), "marker": f"old-{n}"} for n in range(count)]

    def test_regenerate_prunes_to_five_and_keeps_newest(self, fresh, mongo):
        # Backend without a Groq key: regeneration uses the local fallback and never calls the AI.
        url, proc = spawn_backend(GROQ_API_KEY="")
        other = f"other-{uuid.uuid4().hex[:8]}"
        try:
            mongo.plans.delete_many({"user_id": fresh.user_id})
            mongo.plans.insert_many(self.old_plans(fresh.user_id, 7))
            mongo.plans.insert_many(self.old_plans(other, 6))
            resp = requests.post(f"{url}/api/plan/regenerate", json={}, headers=fresh.headers, timeout=60)
            assert resp.status_code == 200, resp.text
            plans = list(mongo.plans.find({"user_id": fresh.user_id}).sort("updated_at", -1))
            assert len(plans) == 5
            assert plans[0].get("marker") is None and plans[0]["updated_at"] == resp.json()["updated_at"], "the new plan is kept"
            assert [p["marker"] for p in plans[1:]] == ["old-6", "old-5", "old-4", "old-3"], "the oldest were deleted"
            assert mongo.plans.count_documents({"user_id": other}) == 6, "other users' plans are untouched"
            for _ in range(2):
                assert requests.post(f"{url}/api/plan/regenerate", json={}, headers=fresh.headers, timeout=60).status_code == 200
            assert mongo.plans.count_documents({"user_id": fresh.user_id}) == 5
        finally:
            stop_backend(proc)
            mongo.plans.delete_many({"user_id": {"$in": [fresh.user_id, other]}})

    def test_first_plan_via_get_is_saved(self, fresh, mongo):
        url, proc = spawn_backend(GROQ_API_KEY="")
        try:
            mongo.plans.delete_many({"user_id": fresh.user_id})
            assert requests.get(f"{url}/api/plan", headers=fresh.headers, timeout=60).status_code == 200
            assert mongo.plans.count_documents({"user_id": fresh.user_id}) == 1
        finally:
            stop_backend(proc)
            mongo.plans.delete_many({"user_id": fresh.user_id})

    def test_save_plan_never_deletes_the_new_plan(self, mongo):
        """Even if the new plan's timestamp sorts oldest, it survives and the total is still 5."""
        user_id = f"cap-{uuid.uuid4().hex[:8]}"
        future = datetime.now(timezone.utc) + timedelta(days=100)
        mongo.plans.insert_many([{"user_id": user_id, "days": [], "updated_at": (future + timedelta(days=n)).isoformat(), "marker": f"future-{n}"} for n in range(6)])

        async def run():
            server.client = AsyncIOMotorClient(server.MONGO_URL)
            server.db = server.client[DB_NAME]
            try:
                await server.save_plan({"user_id": user_id, "days": [], "updated_at": datetime.now(timezone.utc).isoformat(), "marker": "new"})
            finally:
                server.client.close()

        try:
            asyncio.run(run())
            markers = {p["marker"] for p in mongo.plans.find({"user_id": user_id})}
            assert "new" in markers and len(markers) == 5
        finally:
            mongo.plans.delete_many({"user_id": user_id})


class CaptureGroq(BaseHTTPRequestHandler):
    """A fake AI provider that records the request bodies it receives and answers plainly."""

    bodies = []

    def do_POST(self):
        CaptureGroq.bodies.append(json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)))))
        body = json.dumps({"choices": [{"message": {"content": "Capture reply"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class TestHealthConditions:
    """Item 7: stated health conditions reach the plan and coach prompts explicitly, framed as general
    wellness guidance, and the app shows a plain-language disclaimer in English and Telugu."""

    def test_health_conditions_cleaning(self):
        assert server.health_conditions({"conditions": [" PCOS ", "", "diabetes", "x" * 100]}) == ["PCOS", "diabetes", "x" * 60]
        assert server.health_conditions({"conditions": "asthma, thyroid"}) == ["asthma", "thyroid"]
        assert server.health_conditions({}) == []
        assert len(server.health_conditions({"conditions": [str(n) for n in range(30)]})) == 10

    def test_prompts_frame_conditions_as_general_guidance(self):
        profile = {**PROFILE, "conditions": ["PCOS", "diabetes"]}
        context = server.plan_context(profile, [], [], [])
        assert context["health_conditions"] == ["PCOS", "diabetes"]
        assert "health_conditions" in server.PLAN_SYSTEM and "not medical advice" in server.PLAN_SYSTEM
        assert "medically tailored" in server.PLAN_SYSTEM and "never mention medicines" in server.PLAN_SYSTEM
        assert "never name a condition" in server.PLAN_SYSTEM and "supports, manages, treats" in server.PLAN_SYSTEM
        coach = server.coach_system_prompt(profile, "en")
        assert "Self-reported health conditions (user-provided, unverified): PCOS, diabetes." in coach
        assert "not medical advice" in coach and "medically tailored" in coach and "supports, manages, treats" in coach
        assert "has not listed any health conditions" in server.coach_system_prompt(PROFILE, "en")
        assert "Respond in Telugu." in server.coach_system_prompt(PROFILE, "te")

    def test_condition_claims_are_stripped_from_generated_plans(self):
        profile = {**PROFILE, "conditions": ["Type 2 diabetes", "PCOS", "high blood pressure"]}
        fallback = {"reasoning": "Neutral reasoning."}
        plan = {
            "reasoning": "Low-glycaemic meals that align with the user's type-2 diabetes and PCOS.",
            "days": [{"focus": "Supports blood pressure control"}, {"focus": "Protein + fibre balance"}, {"focus": "Diabetic friendly day"}],
        }
        server.strip_condition_claims(plan, profile, fallback)
        assert plan["reasoning"] == "Neutral reasoning."
        assert [day["focus"] for day in plan["days"]] == ["Balanced nutrition", "Protein + fibre balance", "Balanced nutrition"]
        clean = {"reasoning": "High-fibre meals with steady energy.", "days": [{"focus": "High protein"}]}
        server.strip_condition_claims(clean, profile, fallback)
        assert clean["reasoning"] == "High-fibre meals with steady energy." and clean["days"][0]["focus"] == "High protein", "'high' alone is not a condition"
        untouched = {"reasoning": "Mentions diabetes.", "days": []}
        server.strip_condition_claims(untouched, PROFILE, fallback)
        assert untouched["reasoning"] == "Mentions diabetes.", "nothing is stripped when the user listed no conditions"

    def test_conditions_are_sent_to_the_ai_for_plan_and_coach(self, fresh, mongo):
        fake = ThreadingHTTPServer(("127.0.0.1", 0), CaptureGroq)
        threading.Thread(target=fake.serve_forever, daemon=True).start()
        url, proc = spawn_backend(GROQ_API_KEY="fake-key", GROQ_BASE_URL=f"http://127.0.0.1:{fake.server_address[1]}")
        try:
            assert requests.put(f"{url}/api/profile", json={**PROFILE, "conditions": ["PCOS", "hypertension"]}, headers=fresh.headers, timeout=20).status_code == 200
            CaptureGroq.bodies.clear()
            assert requests.post(f"{url}/api/plan/regenerate", json={}, headers=fresh.headers, timeout=60).status_code == 200
            plan_request = CaptureGroq.bodies[-1]["messages"]
            assert "medically tailored" in plan_request[0]["content"]
            user_context = json.loads(plan_request[1]["content"].split("Context: ", 1)[1])
            assert user_context["health_conditions"] == ["PCOS", "hypertension"]
            assert user_context["profile"]["conditions"] == ["PCOS", "hypertension"]
            CaptureGroq.bodies.clear()
            reply = requests.post(f"{url}/api/coach", json={"message": "Dinner idea?", "language": "en"}, headers=fresh.headers, timeout=60)
            assert reply.status_code == 200, reply.text
            system = CaptureGroq.bodies[-1]["messages"][0]["content"]
            assert "PCOS, hypertension" in system and "not medical advice" in system
        finally:
            stop_backend(proc)
            fake.shutdown()
            mongo.coach_messages.delete_many({"user_id": fresh.user_id})
            mongo.plans.delete_many({"user_id": fresh.user_id})
            requests.put(f"{BASE_URL}/api/profile", json=PROFILE, headers=fresh.headers, timeout=20)

    def test_app_shows_the_disclaimer_in_both_languages(self):
        frontend = Path(server.__file__).parent.parent / "frontend"
        i18n = (frontend / "src" / "i18n.ts").read_text(encoding="utf-8")
        english, telugu = i18n.split("  te: {", 1)
        assert "wellnessNotice:" in english and "wellnessNotice:" in telugu
        assert "not medical advice" in english and "not tailored to your medical conditions" in english
        assert "వైద్య సలహా కాదు" in telugu
        assert "t.wellnessNotice" in (frontend / "app" / "(tabs)" / "coach.tsx").read_text(encoding="utf-8")
        assert "t.wellnessNotice" in (frontend / "app" / "(tabs)" / "plan.tsx").read_text(encoding="utf-8")


class TestProgressEditDelete:
    """Item 8: the Today screen edits a logged meal through PATCH /meals/{id}, and the Progress screen lists
    weight entries with a Remove button (DELETE /weight/{id}). The app has no UI test harness, so these
    check the exact requests the screens send plus the strings and wiring in the source."""

    def test_edit_meal_request_sent_by_the_form(self, fresh, mongo):
        meal = fresh.post(f"{BASE_URL}/api/meals", json={"meal_type": "lunch", "name": "Dal rice", "calories": 500, "protein_g": 15, "carbs_g": 80, "fat_g": 10}, timeout=20).json()
        try:
            dash = fresh.get(f"{BASE_URL}/api/dashboard", timeout=20).json()
            assert any(item["id"] == meal["id"] and "protein_g" in item for item in dash["meals"]), "the Today list needs id and macros to prefill the form"
            changes = {"name": "Dal rice with salad", "calories": 430, "protein_g": 17.5, "carbs_g": 70, "fat_g": 9}
            resp = fresh.patch(f"{BASE_URL}/api/meals/{meal['id']}", json=changes, timeout=20)
            assert resp.status_code == 200, resp.text
            assert {key: resp.json()[key] for key in changes} == changes
            assert resp.json()["meal_type"] == "lunch" and resp.json()["date"] == meal["date"], "untouched fields stay as logged"
            after = fresh.get(f"{BASE_URL}/api/dashboard", timeout=20).json()
            assert after["calories"] == 430
            assert fresh.patch(f"{BASE_URL}/api/meals/{meal['id']}", json={**changes, "calories": 99999}, timeout=20).status_code == 422
        finally:
            mongo.meals.delete_many({"user_id": fresh.user_id})

    def test_progress_lists_weight_entries_with_ids_and_delete_works(self, fresh, mongo):
        mongo.weights.delete_many({"user_id": fresh.user_id})
        try:
            first = fresh.post(f"{BASE_URL}/api/weight", json={"weight_kg": 61.5}, timeout=20).json()
            second = fresh.post(f"{BASE_URL}/api/weight", json={"weight_kg": 61.0}, timeout=20).json()
            weights = fresh.get(f"{BASE_URL}/api/progress", timeout=20).json()["weights"]
            assert [item["id"] for item in weights] == [first["id"], second["id"]]
            assert all({"id", "weight_kg", "date"} <= set(item) for item in weights)
            assert fresh.delete(f"{BASE_URL}/api/weight/{first['id']}", timeout=20).status_code == 200
            left = fresh.get(f"{BASE_URL}/api/progress", timeout=20).json()["weights"]
            assert [item["id"] for item in left] == [second["id"]]
        finally:
            mongo.weights.delete_many({"user_id": fresh.user_id})

    def test_screens_are_wired_and_translated(self):
        frontend = Path(server.__file__).parent.parent / "frontend"
        read = lambda *parts: (frontend.joinpath(*parts)).read_text(encoding="utf-8")
        today, progress, form = read("app", "(tabs)", "index.tsx"), read("app", "(tabs)", "progress.tsx"), read("src", "components", "meal-edit-form.tsx")
        assert "patch(`/meals/${id}`" in today and "MealEditForm" in today and "edit-meal-${item.id}" in today
        assert "del(`/weight/${id}`)" in progress and "remove-weight-${item.id}" in progress and "t.weightEntries" in progress
        i18n = read("src", "i18n.ts")
        english, telugu = i18n.split("  te: {", 1)
        used = set(__import__("re").findall(r"\bt\.([A-Za-z]+)", today + progress + form))
        new_keys = {"edit", "save", "cancel", "mealNameLabel", "caloriesLabel", "proteinLabel", "carbsLabel", "fatLabel", "checkNumbers", "mealUpdated", "weightEntries"}
        assert new_keys <= used, new_keys - used
        for key in new_keys:
            assert f"    {key}:" in english and f"    {key}:" in telugu, f"{key} missing in a language"


class TestCoachHistoryRecency:
    """A long conversation must show, and send to the AI, its latest messages, not its first ones."""

    @staticmethod
    def seed(mongo, user_id, count):
        base = datetime.now(timezone.utc) - timedelta(hours=2)
        mongo.coach_messages.delete_many({"user_id": user_id})
        mongo.coach_messages.insert_many([
            {"id": str(uuid.uuid4()), "user_id": user_id, "role": "user" if n % 2 == 0 else "coach", "text": f"message {n:03d}", "created_at": (base + timedelta(seconds=n)).isoformat()}
            for n in range(count)
        ])

    def test_history_returns_the_latest_30_in_order(self, fresh, mongo):
        self.seed(mongo, fresh.user_id, 75)
        try:
            data = requests.get(f"{BASE_URL}/api/coach/history", headers=fresh.headers, timeout=20).json()
            texts = [m["text"] for m in data["messages"]]
            assert texts == [f"message {n:03d}" for n in range(45, 75)]
        finally:
            mongo.coach_messages.delete_many({"user_id": fresh.user_id})

    def test_coach_sends_the_latest_messages_to_the_ai(self, fresh, mongo):
        self.seed(mongo, fresh.user_id, 40)
        fake = ThreadingHTTPServer(("127.0.0.1", 0), CaptureGroq)
        threading.Thread(target=fake.serve_forever, daemon=True).start()
        url, proc = spawn_backend(GROQ_API_KEY="fake-key", GROQ_BASE_URL=f"http://127.0.0.1:{fake.server_address[1]}")
        try:
            CaptureGroq.bodies.clear()
            assert requests.post(f"{url}/api/coach", json={"message": "and now?", "language": "en"}, headers=fresh.headers, timeout=60).status_code == 200
            sent = [m["content"] for m in CaptureGroq.bodies[-1]["messages"][1:]]
            assert sent == [f"message {n:03d}" for n in range(28, 40)] + ["and now?"]
        finally:
            stop_backend(proc)
            fake.shutdown()
            mongo.coach_messages.delete_many({"user_id": fresh.user_id})


class EmptyThenGood(BaseHTTPRequestHandler):
    """Fake AI: "empty" mode answers with no content `empty_first` times, then a normal reply."""

    state = {"empty_first": 1, "hits": 0, "max_tokens": []}

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        EmptyThenGood.state["hits"] += 1
        EmptyThenGood.state["max_tokens"].append(request.get("max_tokens"))
        content = "" if EmptyThenGood.state["hits"] <= EmptyThenGood.state["empty_first"] else "Recovered reply"
        body = json.dumps({"choices": [{"message": {"content": content}, "finish_reason": "length" if not content else "stop"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class TestEmptyAiReply:
    """A reasoning model sometimes returns an empty reply. It is retried, and if it stays empty the user
    gets the structured ai_unavailable error rather than a blank or invented answer."""

    @pytest.fixture(scope="class")
    def backend(self):
        fake = ThreadingHTTPServer(("127.0.0.1", 0), EmptyThenGood)
        threading.Thread(target=fake.serve_forever, daemon=True).start()
        url, proc = spawn_backend(GROQ_API_KEY="fake-key", GROQ_BASE_URL=f"http://127.0.0.1:{fake.server_address[1]}")
        yield url
        stop_backend(proc)
        fake.shutdown()

    def test_empty_reply_is_retried(self, backend, fresh, mongo):
        EmptyThenGood.state.update(empty_first=1, hits=0, max_tokens=[])
        resp = requests.post(f"{backend}/api/coach", json={"message": "hello", "language": "en"}, headers=fresh.headers, timeout=60)
        assert resp.status_code == 200, resp.text
        assert resp.json()["reply"] == "Recovered reply"
        assert EmptyThenGood.state["hits"] == 2
        assert EmptyThenGood.state["max_tokens"][0] == 2000, "the coach leaves room for reasoning tokens"
        mongo.coach_messages.delete_many({"user_id": fresh.user_id})

    def test_always_empty_returns_ai_unavailable_after_two_retries(self, backend, fresh, mongo):
        EmptyThenGood.state.update(empty_first=99, hits=0, max_tokens=[])
        resp = requests.post(f"{backend}/api/coach", json={"message": "hello", "language": "en"}, headers=fresh.headers, timeout=60)
        assert resp.status_code == 503, resp.text
        assert resp.json()["detail"]["code"] == "ai_unavailable"
        assert EmptyThenGood.state["hits"] == 3
        assert mongo.coach_messages.count_documents({"user_id": fresh.user_id}) == 0
