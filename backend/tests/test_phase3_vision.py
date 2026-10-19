"""Phase 3 item 5: photo recognition providers (Gemini default, Groq optional), tested against local fakes."""
import json
import os
import uuid
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient

import vision
from fakes import NUTRITION, FakeProvider, gemini_reply, openai_reply, spawn_backend, stop_backend
from make_test_image import make_food_image

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"

GEMINI_KEY = "fake-gemini-key-xyz-123"
GROQ_KEY = "fake-groq-key-xyz-456"
IMAGE = make_food_image()
KEYS_OFF = {"GEMINI_API_KEY": "", "GROQ_API_KEY": ""}


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=10000)
    yield client.test_database
    client.close()


@pytest.fixture(scope="module")
def session(mongo):
    s = requests.Session()
    resp = s.post(f"{BASE_URL}/api/auth/signup", json={"email": f"vision.{uuid.uuid4().hex[:10]}@example.com", "password": "StrongPass123"}, timeout=20)
    assert resp.status_code == 200, resp.text
    s.headers["Authorization"] = f"Bearer {resp.json()['token']}"
    yield s
    mongo.users.delete_many({"id": resp.json()["user"]["id"]})


def scan(session, url, meal_type="lunch", image=IMAGE):
    return session.post(f"{url}/api/coach/vision", json={"image_base64": image, "language": "en", "meal_type": meal_type}, timeout=60)


class TestHelpers:
    def test_sniff_mime(self):
        assert vision.sniff_mime("/9j/4AAQSkZJRg") == "image/jpeg"
        assert vision.sniff_mime("iVBORw0KGgo") == "image/png"
        assert vision.sniff_mime("UklGRiQAAABXRUJQ") == "image/webp"
        assert vision.sniff_mime("AAAA") == "image/jpeg"

    def test_extract_json(self):
        assert vision.extract_json('{"name": "Idli"}') == {"name": "Idli"}
        assert vision.extract_json('```json\n{"name": "Idli", "calories": 300}\n```') == {"name": "Idli", "calories": 300}
        assert vision.extract_json('<think>maybe {not json} here</think>{"name": "Poha"}') == {"name": "Poha"}
        assert vision.extract_json('Sure! {"name": "Dosa", "alternatives": ["a", "b"]} Enjoy') == {"name": "Dosa", "alternatives": ["a", "b"]}
        for bad in ("", "no json here", "{broken", "{}", "[1, 2]"):
            assert vision.extract_json(bad) is None

    def test_provider_selection(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "g")
        monkeypatch.setenv("GROQ_API_KEY", "q")
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        assert [p.name for p in vision.build_providers()] == ["gemini"], "gemini is the default"
        for setting, expected in (("gemini", ["gemini"]), ("groq", ["groq"]), ("auto", ["gemini", "groq"]), ("AUTO", ["gemini", "groq"]), ("nonsense", ["gemini"])):
            monkeypatch.setenv("VISION_PROVIDER", setting)
            assert [p.name for p in vision.build_providers()] == expected, setting

    def test_defaults_and_overrides(self, monkeypatch):
        for name in ("GEMINI_MODEL", "GROQ_VISION_MODEL", "GEMINI_BASE_URL"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("VISION_PROVIDER", "auto")
        gemini, groq = vision.build_providers()
        assert gemini.model == "gemini-3.8-flash" and groq.model == "qwen/qwen3.8-27b"
        assert gemini.base_url == "https://generativelanguage.googleapis.com"
        monkeypatch.setenv("GEMINI_MODEL", "gemini-test-flash")
        monkeypatch.setenv("GROQ_VISION_MODEL", "some/other-model")
        gemini, groq = vision.build_providers()
        assert gemini.model == "gemini-test-flash" and groq.model == "some/other-model"

    def test_status_never_contains_keys(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "super-secret-gemini")
        monkeypatch.setenv("GROQ_API_KEY", "super-secret-groq")
        monkeypatch.setenv("VISION_PROVIDER", "auto")
        assert "super-secret" not in json.dumps(vision.status())
        assert all(item["configured"] for item in vision.status()["providers"])


class TestGeminiProvider:
    @pytest.fixture(scope="class")
    def gemini(self):
        fake = FakeProvider()
        yield fake
        fake.close()

    @pytest.fixture(scope="class")
    def backend(self, gemini, tmp_path_factory):
        log = tmp_path_factory.mktemp("logs") / "backend.log"
        url, proc = spawn_backend({"VISION_PROVIDER": "gemini", "GEMINI_API_KEY": GEMINI_KEY, "GEMINI_BASE_URL": gemini.url, "GEMINI_MODEL": "gemini-test-flash", "GROQ_API_KEY": ""}, log_path=log)
        yield url, log
        stop_backend(proc)

    def test_request_follows_the_gemini_api(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        resp = scan(session, url, meal_type="dinner")
        assert resp.status_code == 200, resp.text
        sent = gemini.requests[-1]
        assert sent["path"] == "/v1beta/models/gemini-test-flash:generateContent", "no key or query string in the URL"
        assert sent["headers"]["x-goog-api-key"] == GEMINI_KEY
        parts = sent["body"]["contents"][0]["parts"]
        assert "Indian" in parts[0]["text"]
        assert parts[1]["inline_data"] == {"mime_type": "image/jpeg", "data": IMAGE}
        assert sent["body"]["generationConfig"]["response_mime_type"] == "application/json"

    def test_response_shape(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        data = scan(session, url, meal_type="dinner").json()
        assert data["name"] == NUTRITION["name"] and data["calories"] == 520 and data["protein_g"] == 18
        assert data["confidence"] == "medium" and data["alternatives"] == ["Rajma chawal", "Khichdi"]
        assert data["meal_type"] == "dinner"
        assert data["model"] == "gemini-test-flash" and data["provider"] == "gemini"

    def test_png_is_sent_with_its_own_mime_type(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        png_like = "iVBORw0KGgo" + "A" * 300
        assert scan(session, url, image=png_like).status_code == 200
        assert gemini.requests[-1]["body"]["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"

    def test_code_fences_and_thought_parts_are_ignored(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        gemini.queue(200, gemini_reply("```json\n" + json.dumps({**NUTRITION, "name": "Fenced poha"}) + "\n```", thought="thinking {about} json"))
        assert scan(session, url).json()["name"] == "Fenced poha"

    def test_non_numeric_values_fall_back_to_defaults(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        gemini.queue(200, gemini_reply(json.dumps({"name": "Mystery curry", "calories": "about 400", "protein_g": None, "carbs_g": "lots", "confidence": "certain"})))
        resp = scan(session, url)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["calories"] == 350 and data["protein_g"] == 12 and data["carbs_g"] == 40 and data["confidence"] == "medium"

    def test_rate_limit_is_retried(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        gemini.queue(429, {"error": {"message": "quota"}}, {"Retry-After": "0"})
        assert scan(session, url).status_code == 200
        assert len(gemini.requests) == 2

    def test_persistent_failure_is_a_503_not_a_502(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        for _ in range(3):
            gemini.queue(500, {"error": {"message": "boom"}})
        resp = scan(session, url)
        assert resp.status_code == 503, resp.text
        assert resp.json()["detail"]["code"] == "vision_unavailable"
        assert "by hand" in resp.json()["detail"]["message"]
        assert len(gemini.requests) == 3, "first attempt plus 2 retries"

    def test_auth_errors_are_not_retried(self, session, gemini, backend):
        url, _ = backend
        gemini.reset()
        gemini.queue(403, {"error": {"message": "API key not valid"}})
        assert scan(session, url).status_code == 503
        assert len(gemini.requests) == 1

    @pytest.mark.parametrize("reply", [
        {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}},
        {"candidates": [{"content": {"parts": [{"text": ""}]}, "finishReason": "MAX_TOKENS"}]},
        gemini_reply("I cannot tell what this is."),
        gemini_reply("{not valid json"),
    ])
    def test_unusable_answers_are_a_503(self, session, gemini, backend, reply):
        url, _ = backend
        gemini.reset()
        gemini.queue(200, reply)
        resp = scan(session, url)
        assert resp.status_code == 503 and resp.json()["detail"]["code"] == "vision_unavailable"

    def test_image_bytes_and_keys_are_never_logged(self, session, gemini, backend):
        url, log = backend
        gemini.reset()
        gemini.queue(500, {"error": {"message": "boom"}})
        gemini.queue(200, gemini_reply("not json at all"))
        scan(session, url)
        for _ in range(3):
            gemini.queue(500, {"error": {"message": "boom"}})
        scan(session, url)
        text = log.read_text(encoding="utf-8", errors="ignore")
        assert "gemini" in text.lower(), "failures are logged"
        assert IMAGE[:200] not in text and IMAGE[-200:] not in text
        assert GEMINI_KEY not in text

    def test_tiny_images_are_still_rejected(self, session, backend):
        url, _ = backend
        assert session.post(f"{url}/api/coach/vision", json={"image_base64": "aGk=", "language": "en"}, timeout=20).status_code == 422

    def test_signed_out_requests_are_rejected(self, backend):
        url, _ = backend
        assert requests.post(f"{url}/api/coach/vision", json={"image_base64": IMAGE}, timeout=20).status_code == 401


class TestNotConfigured:
    def test_no_provider_is_a_clear_503_and_the_app_still_runs(self, session):
        url, proc = spawn_backend({"VISION_PROVIDER": "gemini", **KEYS_OFF})
        try:
            body = requests.get(f"{url}/api/", timeout=20).json()
            assert body["vision"]["setting"] == "gemini" and body["vision"]["providers"][0]["configured"] is False
            resp = scan(session, url)
            assert resp.status_code == 503, resp.text
            detail = resp.json()["detail"]
            assert detail["code"] == "vision_not_configured"
            assert "isn't set up" in detail["message"] and "by hand" in detail["message"]
            assert session.get(f"{url}/api/me", timeout=20).status_code == 200
        finally:
            stop_backend(proc)

    def test_explicit_gemini_does_not_silently_use_groq(self, session):
        """VISION_PROVIDER=gemini with only a Groq key is 'not configured', rather than quietly using the other provider."""
        url, proc = spawn_backend({"VISION_PROVIDER": "gemini", "GEMINI_API_KEY": "", "GROQ_API_KEY": GROQ_KEY})
        try:
            assert scan(session, url).json()["detail"]["code"] == "vision_not_configured"
        finally:
            stop_backend(proc)


class TestGroqVisionProvider:
    @pytest.fixture(scope="class")
    def groq(self):
        fake = FakeProvider()
        yield fake
        fake.close()

    def test_groq_only(self, session, groq):
        groq.reset()
        url, proc = spawn_backend({"VISION_PROVIDER": "groq", "GEMINI_API_KEY": "", "GROQ_API_KEY": GROQ_KEY, "GROQ_BASE_URL": groq.url})
        try:
            groq.queue(200, openai_reply("<think>hmm {x}</think>" + json.dumps({**NUTRITION, "name": "Groq idli"})))
            resp = scan(session, url)
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["name"] == "Groq idli" and data["provider"] == "groq" and data["model"] == "qwen/qwen3.8-27b"
            sent = groq.requests[-1]
            assert sent["path"] == "/chat/completions" and sent["headers"]["authorization"] == f"Bearer {GROQ_KEY}"
            assert sent["body"]["model"] == "qwen/qwen3.8-27b"
            content = sent["body"]["messages"][0]["content"]
            assert content[1]["image_url"]["url"] == f"data:image/jpeg;base64,{IMAGE}"
        finally:
            stop_backend(proc)

    def test_model_is_configurable(self, session, groq):
        groq.reset()
        url, proc = spawn_backend({"VISION_PROVIDER": "groq", "GEMINI_API_KEY": "", "GROQ_API_KEY": GROQ_KEY, "GROQ_BASE_URL": groq.url, "GROQ_VISION_MODEL": "vendor/other-vision"})
        try:
            assert scan(session, url).json()["model"] == "vendor/other-vision"
            assert groq.requests[-1]["body"]["model"] == "vendor/other-vision"
        finally:
            stop_backend(proc)

    def test_auto_falls_back_from_gemini_to_groq(self, session, groq):
        gemini = FakeProvider()
        groq.reset()
        for _ in range(3):
            gemini.queue(503, {"error": {"message": "overloaded"}}, {"Retry-After": "0"})
        url, proc = spawn_backend({"VISION_PROVIDER": "auto", "GEMINI_API_KEY": GEMINI_KEY, "GEMINI_BASE_URL": gemini.url, "GROQ_API_KEY": GROQ_KEY, "GROQ_BASE_URL": groq.url})
        try:
            data = scan(session, url).json()
            assert data["provider"] == "groq" and len(gemini.requests) == 3
            gemini.reset()
            data = scan(session, url).json()
            assert data["provider"] == "gemini", "Gemini is tried first when it is healthy"
        finally:
            stop_backend(proc)
            gemini.close()

    def test_auto_when_both_fail_is_a_503(self, session, groq):
        gemini = FakeProvider()
        groq.reset()
        gemini.queue(200, gemini_reply("no json"))
        groq.queue(200, openai_reply("still no json"))
        url, proc = spawn_backend({"VISION_PROVIDER": "auto", "GEMINI_API_KEY": GEMINI_KEY, "GEMINI_BASE_URL": gemini.url, "GROQ_API_KEY": GROQ_KEY, "GROQ_BASE_URL": groq.url})
        try:
            resp = scan(session, url)
            assert resp.status_code == 503 and resp.json()["detail"]["code"] == "vision_unavailable"
        finally:
            stop_backend(proc)
            gemini.close()


class TestEmergentVisionRemoved:
    def test_no_emergent_vision_code_or_dependency(self):
        backend = Path(vision.__file__).parent
        for name in ("server.py", "vision.py", "requirements.txt", ".env.example"):
            text = (backend / name).read_text(encoding="utf-8")
            assert "emergentintegrations" not in text and "EMERGENT_LLM_KEY" not in text, name
        assert "pick_vision_model" not in (backend / "server.py").read_text(encoding="utf-8")

    def test_env_example_documents_the_new_settings_with_placeholders_only(self):
        text = (Path(vision.__file__).parent / ".env.example").read_text(encoding="utf-8")
        for key in ("VISION_PROVIDER=gemini", "GEMINI_API_KEY=", "GEMINI_MODEL=gemini-3.8-flash", "GROQ_VISION_MODEL=qwen/qwen3.8-27b"):
            assert key in text, key
        assert "GEMINI_API_KEY=\n" in text, "no key value is committed"


class TestReadme:
    def test_readme_explains_how_to_add_the_key(self):
        readme = (Path(vision.__file__).parent.parent / "README.md").read_text(encoding="utf-8")
        assert "GEMINI_API_KEY" in readme and "aistudio.google.com" in readme and "backend/.env" in readme
        assert "VISION_PROVIDER" in readme and "GROQ_VISION_MODEL" in readme
