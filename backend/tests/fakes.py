"""Local stand-ins for outside services, so tests never need a real API key.

FakeProvider answers like Gemini (POST /v1beta/models/<model>:generateContent) and like Groq's
OpenAI-compatible API (POST /chat/completions), records every request, and can be scripted to fail.
"""
import json
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent

NUTRITION = {
    "name": "Dal tadka with rice",
    "portion": "1 plate",
    "calories": 520,
    "protein_g": 18,
    "carbs_g": 80,
    "fat_g": 12,
    "confidence": "medium",
    "alternatives": ["Rajma chawal", "Khichdi"],
}


def gemini_reply(text: str, thought: Optional[str] = None) -> Dict[str, Any]:
    parts = [{"text": text}]
    if thought is not None:
        parts.insert(0, {"text": thought, "thought": True})
    return {"candidates": [{"content": {"parts": parts, "role": "model"}, "finishReason": "STOP"}]}


def openai_reply(text: str) -> Dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}


class FakeProvider:
    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.script: List[Tuple[int, Dict[str, Any], Dict[str, str]]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                owner.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
                if owner.script:
                    status, payload, headers = owner.script.pop(0)
                elif ":generateContent" in self.path:
                    status, payload, headers = 200, gemini_reply(json.dumps(NUTRITION)), {}
                else:
                    status, payload, headers = 200, openai_reply(json.dumps(NUTRITION)), {}
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def queue(self, status: int, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> None:
        self.script.append((status, payload, headers or {}))

    def reset(self) -> None:
        self.requests.clear()
        self.script.clear()

    def close(self) -> None:
        self.server.shutdown()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def spawn_backend(env: Optional[Dict[str, str]] = None, log_path: Optional[Path] = None):
    """Start another backend (same database) with extra environment; returns (url, process).

    Passing "" for a key blanks it, because values already in the environment win over backend/.env."""
    import os

    port = free_port()
    sink = open(log_path, "wb") if log_path else subprocess.DEVNULL
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND_DIR,
        env={**os.environ, **(env or {})},
        stdout=sink,
        stderr=subprocess.STDOUT if log_path else subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            if requests.get(f"{url}/api/", timeout=1).status_code == 200:
                return url, proc
        except requests.RequestException:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("backend did not start")


def stop_backend(proc) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
