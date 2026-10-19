"""Phase 2 backend-hardening regression tests.

Same approach as test_phase1_fixes.py: integration tests against the live server
(EXPO_PUBLIC_BACKEND_URL) and the same MongoDB (test_database), with a fresh throwaway
user per module run. Pure helpers are unit-tested by importing server directly.
"""
import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

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
