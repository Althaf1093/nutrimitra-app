"""Regression guards for bugs the browser end-to-end run (e2e/) found in the app.

The app has no unit-test harness, so each guard checks the source for the fix; the real behaviour is proved by the
Playwright suite in e2e/, which fails on any unexpected console error or failed request."""
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def read(*parts):
    return FRONTEND.joinpath(*parts).read_text(encoding="utf-8")


class TestNoRequestWithoutAToken:
    """First visit: the app called GET /api/me with no token, got a 401 and logged a console error."""

    def test_boot_checks_for_a_saved_token_before_asking_the_backend(self):
        auth = read("src", "context", "auth.tsx")
        boot = auth[auth.index("const boot = async () => {"):]
        assert boot.index("await getToken()") < boot.index("await applySession()")
        assert 'setStatus("anon")' in boot[: boot.index("await applySession()")]
        assert "getToken" in auth[: auth.index("export function AuthProvider")], "imported from the api module"


class TestNoNotificationsWarningOnWeb:
    """expo-notifications logs a warning in the browser just from being imported."""

    def test_the_package_is_only_loaded_on_devices(self):
        text = read("src", "lib", "notifications.ts")
        assert 'import * as Notifications from "expo-notifications"' not in text
        assert 'import type * as NotificationsModule from "expo-notifications"' in text
        assert 'Platform.OS === "web" ? (undefined as never) : require("expo-notifications")' in text

    def test_every_runtime_use_is_behind_a_native_check(self):
        text = read("src", "lib", "notifications.ts")
        for name in ("applyReminders", "clearReminders", "ensureReminderPermissions"):
            body = text[text.index(f"export async function {name}"):]
            assert 'Platform.OS === "web"' in body[:200], name
        assert 'if (Platform.OS !== "web") {\n  Notifications.setNotificationHandler' in text.replace("\r\n", "\n")
        # scheduleDaily / scheduleInterval are only called from applyReminders, which returns early on web
        assert "scheduleDaily(" in text and text.index("export async function applyReminders") < text.rindex("scheduleDaily(")


class TestSignOutResetsNavigation:
    """After sign-out and sign-in the old tabs stayed in the navigation stack, so two Today screens were mounted."""

    def test_sign_out_clears_the_whole_navigation_stack(self):
        settings = read("app", "settings.tsx")
        handler = settings[settings.index('testID="sign-out-button"'):][:900]
        assert handler.index("await signOut()") < handler.index("router.dismissAll()") < handler.index('router.replace("/")')


class TestNoRequestsWithoutSignIn:
    """After sign-out the Today screen reloaded and called the backend with no token (401s in the console)."""

    def test_api_refuses_to_send_signed_in_requests_without_a_token(self):
        api = read("src", "api.ts")
        guard = api[api.index("const token = await getToken();"):][:600]
        assert '!path.startsWith("/auth/")' in guard and "no_token" in guard
        assert guard.index("no_token") < api.index("await fetch(", api.index("const token = await getToken();"))


class TestSettingsTogglesCannotOverwriteSavedValues:
    """E2E flow 9: toggling analytics, then coach memory, left analytics off on the server. Settings starts with default
    values and posted all four, so a tap before the saved values arrived (or from a stale copy) overwrote the others."""

    def test_only_the_changed_key_is_sent_and_toggles_wait_for_the_saved_values(self):
        settings = read("app", "settings.tsx")
        update = settings[settings.index("const updatePermission"):][:420]
        assert "if (!loaded.permissions) return;" in update
        assert 'post("/permissions", { [key]: value })' in update
        assert 'post("/permissions", next)' not in settings
        assert settings.count("disabled={!loaded.permissions}") == 4 and settings.count("disabled={!loaded.reminders}") == 4
        assert "if (!loaded.reminders) return;" in settings[settings.index("const updateReminder"):][:200]


class TestPermissionsEndpointKeepsOtherKeys:
    """The server side of the same bug: posting one key must leave the other saved keys alone."""

    def test_posting_one_permission_does_not_change_the_others(self):
        import os
        import uuid

        import requests

        base = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
        user = requests.post(f"{base}/api/auth/signup", json={"email": f"perm.{uuid.uuid4().hex[:10]}@example.com", "password": "StrongPass123"}, timeout=20).json()
        headers = {"Authorization": f"Bearer {user['token']}"}
        try:
            requests.post(f"{base}/api/permissions", json={"health_sync": True, "analytics": True}, headers=headers, timeout=20)
            requests.post(f"{base}/api/permissions", json={"coach_memory": False}, headers=headers, timeout=20)
            saved = requests.get(f"{base}/api/permissions", headers=headers, timeout=20).json()
            assert saved["health_sync"] is True and saved["analytics"] is True and saved["coach_memory"] is False
        finally:
            from pymongo import MongoClient

            db = MongoClient("mongodb://127.0.0.1:27017").test_database
            db.permissions.delete_many({"user_id": user["user"]["id"]})
            db.users.delete_many({"id": user["user"]["id"]})


class TestTeluguLeftoversFoundInTheBrowser:
    """E2E flow 9 scans every main screen in Telugu. It found 'active' in the progress ring, the plan goal shown as the
    stored English value, and the weekly review sentence, which came from the backend in English."""

    def test_ring_caption_goal_and_weekly_review_use_the_catalogue(self):
        assert "{t.activeWord} {t.minutes}" in read("src", "components", "today-progress-card.tsx")
        assert "optionLabel(t, plan.goal)" in read("app", "(tabs)", "plan.tsx")
        progress = read("app", "(tabs)", "progress.tsx")
        assert "t.weeklyReview" in progress and "progress?.review" not in progress

    def test_new_keys_exist_in_both_languages(self):
        i18n = read("src", "i18n.ts")
        english, telugu = i18n.split("  te: {", 1)
        for key in ("activeWord", "weeklyReview"):
            assert f"    {key}:" in english and f"    {key}:" in telugu
