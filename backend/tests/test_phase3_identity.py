"""Phase 3 identity checks: the app is called Wellstride everywhere users can see it, and the
store identifiers are the agreed ones. Internal names (repo, DB, storage keys) are intentionally unchanged."""
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")

# Internal identifiers that must keep the old name (changing them would sign users out or orphan data).
INTERNAL_OK = ("nutrimitra.session.token", "nutrimitra.lang")


def user_visible_files():
    for folder in (FRONTEND / "app", FRONTEND / "src"):
        for path in folder.rglob("*"):
            if path.suffix in {".ts", ".tsx"}:
                yield path


class TestIdentity:
    def test_app_json_identifiers(self):
        expo = json.loads((FRONTEND / "app.json").read_text(encoding="utf-8"))["expo"]
        assert expo["name"] == "Wellstride"
        assert expo["slug"] == "wellstride"
        assert expo["scheme"] == "wellstride"
        assert expo["ios"]["bundleIdentifier"] == "in.inkbrief.wellstride"
        assert expo["android"]["package"] == "in.inkbrief.wellstride"
        assert "emergent" not in json.dumps(expo).lower()

    def test_no_old_name_in_user_visible_code(self):
        offenders = []
        for path in user_visible_files():
            text = path.read_text(encoding="utf-8")
            for key in INTERNAL_OK:
                text = text.replace(key, "")
            if re.search(r"nutrimitra", text, re.IGNORECASE):
                offenders.append(str(path.relative_to(ROOT)))
        assert offenders == [], offenders

    def test_both_languages_use_the_new_name(self):
        i18n = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
        english, telugu = i18n.split("  te: {", 1)
        assert "Wellstride" in english and "Wellstride" in telugu

    def test_readme_title(self):
        assert (ROOT / "README.md").read_text(encoding="utf-8").splitlines()[0] == "# Wellstride"

    def test_status_endpoint_name(self):
        assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"
        body = requests.get(f"{BASE_URL}/api/", timeout=20).json()
        assert body["name"] == "Wellstride"
