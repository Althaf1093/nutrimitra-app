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
