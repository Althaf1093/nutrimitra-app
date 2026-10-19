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


class TestEmergentCleanup:
    """Item 2: the Emergent scaffolding is gone and nothing refers to it (Google login is replaced in item 6)."""

    def test_files_are_removed(self):
        for name in (".emergent", "test_reports", "test_result.md", "image_testing.md", ".gitconfig"):
            assert not (ROOT / name).exists(), name
        scripts = FRONTEND / "scripts"
        assert not list(scripts.glob("*guard*")) and not (scripts / "sync-shims.sh").exists()

    def test_install_has_no_preinstall_hook(self):
        package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
        assert "preinstall" not in package["scripts"]
        assert "cmd-guard" not in json.dumps(package)

    def test_nothing_references_the_removed_files(self):
        pattern = re.compile(r"cmd-guard|install-guard|sync-shims|image_testing|test_result\.md|\.emergent/")
        offenders = []
        for folder in (FRONTEND / "app", FRONTEND / "src", ROOT / "backend", FRONTEND / "package.json", FRONTEND / "app.json"):
            files = [folder] if folder.is_file() else [p for p in folder.rglob("*") if p.suffix in {".py", ".ts", ".tsx", ".js", ".json"} and ".venv" not in p.parts and "node_modules" not in p.parts and "__pycache__" not in p.parts]
            for path in files:
                if path.name == "test_phase3_identity.py":
                    continue
                if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                    offenders.append(str(path.relative_to(ROOT)))
        assert offenders == [], offenders


class TestPlaceholderBranding:
    """Item 3: generated placeholder icons with the right sizes and theme colours; template images are gone."""

    GREEN = (74, 107, 93)
    CREAM = (253, 251, 247)

    @staticmethod
    def image(*parts):
        from PIL import Image

        return Image.open(FRONTEND.joinpath(*parts))

    def test_sizes_and_modes(self):
        icon = self.image("assets", "images", "icon.png")
        assert icon.size == (1024, 1024) and icon.mode == "RGB", "the iOS icon must be opaque"
        assert self.image("assets", "images", "adaptive-icon.png").size == (1024, 1024)
        assert self.image("assets", "images", "adaptive-icon.png").mode == "RGBA"
        assert self.image("assets", "images", "splash-image.png").size == (1024, 1024)
        assert self.image("assets", "images", "favicon.png").size == (48, 48)
        assert self.image("assets", "store", "icon-512.png").size == (512, 512)

    def test_theme_colours(self):
        icon = self.image("assets", "images", "icon.png")
        assert icon.getpixel((20, 20)) == self.GREEN
        assert max(icon.getdata(), key=lambda px: sum(px)) == self.CREAM, "the mark is cream"
        assert self.image("assets", "images", "splash-image.png").getpixel((20, 20)) == self.CREAM

    def test_adaptive_icon_stays_in_the_safe_zone(self):
        import math

        adaptive = self.image("assets", "images", "adaptive-icon.png")
        assert adaptive.getpixel((5, 5))[3] == 0, "the foreground is transparent so the green background shows"
        left, top, right, bottom = adaptive.getchannel("A").getbbox()
        farthest = max(math.hypot(x - 512, y - 512) for x, y in ((left, top), (right, top), (left, bottom), (right, bottom)))
        assert farthest < 0.33 * 1024, "Android crops adaptive icons to about the middle 66%"
        assert left > 100 and right < 924

    def test_app_json_uses_the_theme_not_black(self):
        expo = json.loads((FRONTEND / "app.json").read_text(encoding="utf-8"))["expo"]
        assert expo["android"]["adaptiveIcon"]["backgroundColor"].lower() == "#4a6b5d"
        splash = next(plugin[1] for plugin in expo["plugins"] if isinstance(plugin, list) and plugin[0] == "expo-splash-screen")
        assert splash["backgroundColor"].lower() == "#fdfbf7"
        assert (FRONTEND / expo["icon"]).exists() and (FRONTEND / expo["web"]["favicon"]).exists()
        assert (FRONTEND / expo["android"]["adaptiveIcon"]["foregroundImage"]).exists()
        assert (FRONTEND / splash["image"]).exists()

    def test_template_images_are_removed_and_nothing_references_them(self):
        images = {path.name for path in (FRONTEND / "assets" / "images").iterdir()}
        assert images == {"icon.png", "adaptive-icon.png", "splash-image.png", "favicon.png"}
        pattern = re.compile(r"partial-react-logo|react-logo|app-image")
        for path in user_visible_files():
            assert not pattern.search(path.read_text(encoding="utf-8")), path

    def test_generator_script_is_committed_and_reproduces_the_assets(self):
        script = FRONTEND / "scripts" / "make-icons.py"
        assert script.exists()
        text = script.read_text(encoding="utf-8")
        assert "#4A6B5D" in text and "#FDFBF7" in text
