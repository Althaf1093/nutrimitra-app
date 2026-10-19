"""Phase 4 item 1: the Privacy Policy, Terms and delete-account pages are public HTML served by the backend."""
import requests


def get(p4, path):
    return requests.get(f"{p4.url}{path}", timeout=20)


def test_pages_are_public_html(p4):
    for path in ("/privacy", "/terms", "/delete-account"):
        response = get(p4, path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html"), path
        assert "Wellstride" in response.text


def test_privacy_policy_covers_the_required_points(p4):
    text = get(p4, "/privacy").text
    for phrase in (
        "18 and over",
        "health conditions",
        "meal photos",
        "Google (Gemini)",
        "Groq",
        "not medical advice",
        "Delete account",
        "Digital Personal Data Protection",
        "Access",
        "Correction",
        "Grievance",
        "encrypted",
        "bcrypt",
        "up to 30 days",
        "Coach messages",
    ):
        assert phrase.lower() in text.lower(), phrase


def test_terms_cover_age_and_medical_disclaimer(p4):
    text = get(p4, "/terms").text
    assert "18 or over" in text
    assert "not medical advice" in text
    assert "/privacy" in text


def test_delete_account_page_explains_the_steps(p4):
    text = get(p4, "/delete-account").text
    assert "Delete account" in text and "DELETE" in text
    assert "help@wellstride.test" in text


def test_support_email_comes_from_the_environment(p4):
    for path in ("/privacy", "/terms", "/delete-account"):
        assert "help@wellstride.test" in get(p4, path).text
    assert "support@inkbrief.in" not in get(p4, "/privacy").text


def test_default_support_email_is_a_placeholder(monkeypatch):
    import legal

    monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
    assert legal.support_email() == "support@inkbrief.in"
    assert "support@inkbrief.in" in legal.render("privacy")


def test_pages_need_no_login_and_are_not_in_the_api_docs(p4):
    assert requests.get(f"{p4.url}/privacy", timeout=20, headers={}).status_code == 200
    assert "/privacy" not in requests.get(f"{p4.url}/openapi.json", timeout=20).json()["paths"]
