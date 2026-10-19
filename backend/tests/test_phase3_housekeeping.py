"""Phase 3 item 8: housekeeping. No blanket log suppression, and no unused packages left in the app."""
import json
import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
PACKAGE = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
DEPENDENCIES = {**PACKAGE["dependencies"], **PACKAGE.get("devDependencies", {})}
REMOVED = ["date-fns", "dayjs", "expo-blur", "expo-haptics", "expo-linear-gradient", "react-native-dotenv", "react-native-webview", "@tanstack/react-query"]
# Needed even though no app file imports them directly (checked against installed peer dependencies).
KEPT_FOR_PEERS = {"expo-linking": "peer dependency of expo-router and expo-auth-session"}


def app_files():
    for folder in (FRONTEND / "app", FRONTEND / "src"):
        for path in folder.rglob("*"):
            if path.suffix in {".ts", ".tsx", ".js"}:
                yield path


class TestLogBox:
    def test_warnings_are_no_longer_hidden(self):
        offenders = [str(p.relative_to(FRONTEND)) for p in app_files() if "LogBox" in p.read_text(encoding="utf-8")]
        assert offenders == []


class TestUnusedPackagesRemoved:
    def test_removed_packages_are_gone_from_package_json(self):
        assert [name for name in REMOVED if name in DEPENDENCIES] == []

    def test_removed_packages_are_gone_from_the_lockfile(self):
        lock = (FRONTEND / "yarn.lock").read_text(encoding="utf-8")
        for name in REMOVED:
            assert not re.search(rf'^"?{re.escape(name)}@', lock, re.M), f"{name} is still in yarn.lock"

    def test_nothing_imports_a_removed_package(self):
        for path in app_files():
            text = path.read_text(encoding="utf-8")
            for name in REMOVED:
                assert f'"{name}' not in text and f"'{name}" not in text, (path.name, name)

    def test_react_query_provider_and_client_are_gone(self):
        assert not (FRONTEND / "src" / "query-client.ts").exists()
        assert "QueryClient" not in (FRONTEND / "app" / "_layout.tsx").read_text(encoding="utf-8")

    def test_every_remaining_direct_dependency_is_used_or_explained(self):
        """Packages that are in package.json but not imported must be plugins/peers listed in app.json or here."""
        app_json = (FRONTEND / "app.json").read_text(encoding="utf-8")
        source = "\n".join(p.read_text(encoding="utf-8") for p in app_files())
        for name in KEPT_FOR_PEERS:
            assert name in DEPENDENCIES, name
        for name in ("expo-auth-session", "expo-crypto", "expo-web-browser", "expo-router", "expo-image"):
            assert name in DEPENDENCIES and (f'"{name}' in source or name in app_json), name


class TestVersionsAreAligned:
    def test_expo_packages_use_patch_versions_expo_doctor_expects(self):
        expected = {"expo": "57.0.30", "expo-router": "57.0.28", "expo-constants": "57.0.22", "expo-linking": "57.0.13", "expo-web-browser": "57.0.3", "expo-font": "57.0.4"}
        for name, version in expected.items():
            assert DEPENDENCIES[name].lstrip("~^") == version, (name, DEPENDENCIES[name])
