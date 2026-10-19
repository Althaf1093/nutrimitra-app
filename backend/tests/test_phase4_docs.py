"""Phase 4 item 6: the Play Data Safety and listing drafts exist and stay in step with the real code and app.json."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAFETY = (ROOT / "docs" / "PLAY_DATA_SAFETY.md").read_text(encoding="utf-8")
LISTING = (ROOT / "docs" / "PLAY_STORE_LISTING.md").read_text(encoding="utf-8")


def test_every_android_permission_is_explained():
    permissions = json.loads((ROOT / "frontend" / "app.json").read_text(encoding="utf-8"))["expo"]["android"]["permissions"]
    for permission in permissions:
        short = permission.rsplit(".", 1)[-1]
        assert short in SAFETY, f"{short} is in app.json but not in PLAY_DATA_SAFETY.md"


def test_data_safety_covers_the_data_and_the_third_parties():
    for phrase in ("Email address", "Health info", "Fitness info", "Photos", "Gemini", "Groq", "not stored", "HTTPS", "Delete account", "/delete-account", "/privacy", "SUPPORT_EMAIL"):
        assert phrase in SAFETY, phrase
    assert "Draft for review" in SAFETY and "Draft for review" in LISTING


def test_listing_text_fits_the_store_limits():
    short = next(line for line in LISTING.split("\n## Short description")[1].splitlines() if line.startswith("> "))[2:]
    assert len(short) <= 80, len(short)
    full = "\n".join(line for line in LISTING.split("\n## Full description")[1].split("\n## ")[0].splitlines() if line.startswith(">"))
    assert 500 < len(full) < 4000
    assert "Health & Fitness" in LISTING and "18 and over" in LISTING and "not medical advice" in LISTING
    assert "Health Connect" in LISTING and "Content rating" in LISTING


def test_documented_deletion_and_policy_urls_match_the_server_routes():
    import server

    paths = {route.path for route in server.app.routes}
    for path in ("/privacy", "/terms", "/delete-account"):
        assert path in paths
