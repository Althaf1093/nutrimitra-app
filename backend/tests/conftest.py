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
