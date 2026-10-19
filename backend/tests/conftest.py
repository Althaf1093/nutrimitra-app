import pytest

import server
from fakes import FakeProvider, spawn_backend, stop_backend

FAKE_GEMINI_KEY = "fake-gemini-key-for-tests"


@pytest.fixture(scope="session")
def vision_backend():
    """A backend whose photo recognition talks to a local fake Gemini, so photo tests need no real key.

    Sign-in tokens are signed with the shared JWT secret, so a session logged in on the main test server
    also works here."""
    fake = FakeProvider()
    url, proc = spawn_backend({"VISION_PROVIDER": "gemini", "GEMINI_API_KEY": FAKE_GEMINI_KEY, "GEMINI_BASE_URL": fake.url, "GROQ_API_KEY": ""})
    yield url
    stop_backend(proc)
    fake.close()


@pytest.fixture(scope="session")
def google_backend():
    """A backend with Google sign-in switched on (one client ID), for tests that send it bad tokens."""
    url, proc = spawn_backend({"GOOGLE_CLIENT_IDS": "test-client.apps.googleusercontent.com"})
    yield url
    stop_backend(proc)


@pytest.fixture(autouse=True)
def restore_server_database():
    """Some tests point server.client / server.db at a scratch Mongo client inside their own event loop and then
    close it. Put the originals back after every test so a later in-process test never inherits a closed loop."""
    client, db = server.client, server.db
    yield
    server.client, server.db = client, db


class Phase4Backend:
    def __init__(self, url, email):
        self.url = url
        self.email = email  # a FakeProvider standing in for Resend: every email the backend sends is in .requests


@pytest.fixture(scope="session")
def p4():
    """A backend for the Phase 4 features: a placeholder support address, and email going to a local fake of Resend."""
    fake = FakeProvider()
    url, proc = spawn_backend({
        "SUPPORT_EMAIL": "help@wellstride.test",
        "RESEND_API_KEY": "re_fake_key_for_tests",
        "RESEND_BASE_URL": fake.url,
        "EMAIL_FROM": "Wellstride <noreply@wellstride.test>",
        "GOOGLE_CLIENT_IDS": "",
        "AUTH_RATE_LIMIT_EXEMPT_IPS": "127.0.0.1,::1",
    })
    yield Phase4Backend(url, fake)
    stop_backend(proc)
    fake.close()
