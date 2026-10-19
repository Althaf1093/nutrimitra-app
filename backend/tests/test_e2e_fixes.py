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
