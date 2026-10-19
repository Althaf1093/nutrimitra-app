"""Starts everything the browser tests need, on their own ports and their own database:

    fake AI provider   (fake_ai.py)       E2E_AI_PORT   default 8103
    backend            (backend/server.py) E2E_API_PORT  default 8101, database wellstride_e2e
    web build          (static, from `expo export`)  E2E_WEB_PORT default 8102

Run by Playwright's global setup, or by hand:  python stack.py            (stays running; Ctrl+C to stop)
                                               python stack.py --rebuild  (rebuild the web build first)
                                               python stack.py --cleanup  (drop the test database)

Environment: E2E_PYTHON (python with the backend's packages; default backend/.venv), E2E_CORS (set CORS_ORIGINS on the
backend; unset = the backend's own default, which is what real users get).
Never reads or prints backend/.env: the backend loads it itself, and the AI keys are overridden with fakes.
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

E2E = Path(__file__).resolve().parent
ROOT = E2E.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
WEB = E2E / ".web"
LOGS = E2E / ".logs"

API_PORT = int(os.environ.get("E2E_API_PORT", "8101"))
WEB_PORT = int(os.environ.get("E2E_WEB_PORT", "8102"))
AI_PORT = int(os.environ.get("E2E_AI_PORT", "8103"))
DB_NAME = os.environ.get("E2E_DB", "wellstride_e2e")
API_URL = f"http://localhost:{API_PORT}"


def backend_python() -> str:
    if os.environ.get("E2E_PYTHON"):
        return os.environ["E2E_PYTHON"]
    windows = BACKEND / ".venv" / "Scripts" / "python.exe"
    return str(windows if windows.exists() else BACKEND / ".venv" / "bin" / "python")


def wait_for(url: str, name: str, seconds: int = 90) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2).read()
            return
        except Exception:
            time.sleep(0.5)
    raise SystemExit(f"{name} did not start at {url}; see {LOGS}")


def build_web(rebuild: bool) -> None:
    marker = WEB / ".backend-url"
    if not rebuild and (WEB / "index.html").exists() and marker.exists() and marker.read_text().strip() == API_URL:
        print("web build is up to date", flush=True)
        return
    print("building the web app (about a minute)...", flush=True)
    env = {**os.environ, "EXPO_PUBLIC_BACKEND_URL": API_URL, "EXPO_PUBLIC_GOOGLE_CLIENT_ID": "", "CI": "1"}
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "web-build.log", "wb") as log:
        result = subprocess.run("npx expo export --platform web --clear --output-dir " + f'"{WEB}"', cwd=FRONTEND, env=env, shell=True, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise SystemExit(f"web build failed; see {LOGS / 'web-build.log'}")
    marker.write_text(API_URL)


class SpaHandler(SimpleHTTPRequestHandler):
    """Serves the exported app; unknown paths get index.html, like a single-page app host."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path.split("?")[0])
        if not os.path.exists(path) or os.path.isdir(path) and not os.path.exists(os.path.join(path, "index.html")):
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, *args):
        pass


def cleanup_database() -> None:
    from pymongo import MongoClient

    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=5000)
    users = client[DB_NAME].users.count_documents({}) if DB_NAME in client.list_database_names() else 0
    client.drop_database(DB_NAME)
    print(f"dropped database {DB_NAME} ({users} throwaway users removed)", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if args.cleanup:
        cleanup_database()
        return

    LOGS.mkdir(exist_ok=True)
    build_web(args.rebuild)
    children = []
    try:
        ai = subprocess.Popen([sys.executable, str(E2E / "fake_ai.py"), str(AI_PORT)], stdout=open(LOGS / "fake-ai.log", "wb"), stderr=subprocess.STDOUT)
        children.append(ai)
        env = {
            **os.environ,
            "DB_NAME": DB_NAME,
            "GROQ_API_KEY": "fake-groq-key",
            "GROQ_BASE_URL": f"http://127.0.0.1:{AI_PORT}",
            "VISION_PROVIDER": "gemini",
            "GEMINI_API_KEY": "fake-gemini-key",
            "GEMINI_BASE_URL": f"http://127.0.0.1:{AI_PORT}",
            "GOOGLE_CLIENT_IDS": "",
            # The real limit settings, with no loopback exemption so the rate-limit flow is genuine; a 1 minute window
            # lets that flow also show a person getting back in.
            "AUTH_RATE_LIMIT": "10",
            "AUTH_RATE_WINDOW_MINUTES": "1",
            "AUTH_RATE_LIMIT_EXEMPT_IPS": "",
        }
        if os.environ.get("E2E_CORS"):
            env["CORS_ORIGINS"] = os.environ["E2E_CORS"]
        else:
            env.pop("CORS_ORIGINS", None)
        backend = subprocess.Popen([backend_python(), "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(API_PORT)], cwd=BACKEND, env=env, stdout=open(LOGS / "backend.log", "wb"), stderr=subprocess.STDOUT)
        children.append(backend)
        web = ThreadingHTTPServer(("127.0.0.1", WEB_PORT), SpaHandler)
        import threading

        threading.Thread(target=web.serve_forever, daemon=True).start()
        wait_for(f"http://127.0.0.1:{AI_PORT}/__state", "fake AI")
        wait_for(f"http://127.0.0.1:{API_PORT}/api/", "backend")
        wait_for(f"http://127.0.0.1:{WEB_PORT}/", "web server")
        print(f"READY web=http://localhost:{WEB_PORT} api={API_URL} ai=http://127.0.0.1:{AI_PORT}", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(1)
        raise SystemExit("a service stopped unexpectedly; see " + str(LOGS))
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
        try:
            cleanup_database()
        except Exception as exc:  # the database may already be gone
            print("cleanup skipped:", exc)


if __name__ == "__main__":
    main()
