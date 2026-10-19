"""A scriptable fake of the AI providers, so end-to-end runs are deterministic and never touch a real API.

Answers like Groq (POST /chat/completions) and Gemini (POST /v1beta/models/<model>:generateContent).
Switch its behaviour while a test runs:

    POST /__mode   {"mode": "ok" | "busy"}    busy = every call gets HTTP 429, like a rate limit
    GET  /__state                              {"mode": ..., "counts": {...}}
    POST /emails                               fake of Resend: the message is kept, whatever the mode
    GET  /__emails?to=<address>                the messages sent to that address, oldest first

Standard library only.
"""
import json
import sys
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EMAILS = []
STATE = {"mode": "ok", "counts": {"plan": 0, "coach": 0, "vision": 0, "rejected": 0}}

MEALS = {
    "breakfast": ["Moong dal chilla", "Vegetable poha", "Idli with sambar", "Besan cheela", "Oats upma", "Ragi dosa", "Paneer paratha"],
    "lunch": ["Rajma rice bowl", "Dal palak with roti", "Chole salad bowl", "Vegetable pulao with raita", "Sambar rice", "Paneer tikka wrap", "Millet khichdi"],
    "snack": ["Roasted chana", "Fruit and almonds", "Sprouts chaat", "Buttermilk with makhana", "Peanut chikki", "Cucumber hummus", "Fruit yogurt bowl"],
    "dinner": ["Vegetable khichdi", "Tofu stir-fry with roti", "Lauki dal with rice", "Mixed veg curry with roti", "Vegetable soup with paneer", "Palak paneer with roti", "Bisi bele bath"],
}
KCAL = {"breakfast": 420, "lunch": 560, "snack": 180, "dinner": 480}


def plan_json(context=None):
    """A plan like the real model would write. When the request lists the person's kitchen, every meal names ingredients from it."""
    kitchen = (context or {}).get("kitchen_items") or []
    days = []
    for number in range(1, 8):
        meals = []
        for meal_type in ("breakfast", "lunch", "snack", "dinner"):
            kcal = KCAL[meal_type] + number * 5
            ingredients = [kitchen[(number + offset) % len(kitchen)] for offset in range(min(3, len(kitchen)))] if kitchen else None
            meals.append({
                **({"ingredients": ingredients} if ingredients else {}),
                "type": meal_type,
                "name": MEALS[meal_type][number - 1],
                "portion": "1 serving",
                "calories": kcal,
                "protein_g": round(kcal * 0.18 / 4),
                "carbs_g": round(kcal * 0.52 / 4),
                "fat_g": round(kcal * 0.30 / 9),
            })
        days.append({"day": number, "title": f"Day {number}", "focus": "Balanced Indian meals", "meals": meals})
    return json.dumps({"days": days, "reasoning": "Familiar Indian meals with fibre and protein for steady energy."})


NUTRITION = {"name": "Dal tadka with rice", "portion": "1 plate", "calories": 520, "protein_g": 18, "carbs_g": 80, "fat_g": 12, "confidence": "medium", "alternatives": ["Rajma chawal", "Khichdi"]}


def chat_reply(body):
    messages = body.get("messages", [])
    system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    if "planning engine" in system:
        STATE["counts"]["plan"] += 1
        context = {}
        if "Context: " in last_user:
            try:
                context = json.loads(last_user.split("Context: ", 1)[1])
            except ValueError:
                context = {}
        return plan_json(context)
    STATE["counts"]["coach"] += 1
    text = "Fake coach: try a balanced plate with dal, vegetables and one roti."
    if "recipe" in last_user.lower():
        recipe = {"name": "Quick vegetable khichdi", "time_min": 25, "calories": 380, "protein_g": 14, "carbs_g": 62, "fat_g": 8, "ingredients": ["rice", "moong dal", "vegetables"], "steps": ["Wash rice and dal.", "Pressure cook with vegetables."]}
        text += "\n```recipe\n" + json.dumps(recipe) + "\n```"
    return text


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, payload, headers=None):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/__emails":
            address = parse_qs(url.query).get("to", [""])[0]
            return self.respond(200, [m for m in EMAILS if address in m.get("to", [])])
        self.respond(200, STATE)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/__mode":
            STATE["mode"] = body.get("mode", "ok")
            return self.respond(200, STATE)
        if self.path == "/emails":
            EMAILS.append(body)
            return self.respond(200, {"id": f"fake-{len(EMAILS)}"})
        if STATE["mode"] == "busy":
            STATE["counts"]["rejected"] += 1
            return self.respond(429, {"error": {"message": "Rate limit reached"}}, {"Retry-After": "0"})
        if ":generateContent" in self.path:
            STATE["counts"]["vision"] += 1
            return self.respond(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(NUTRITION)}]}, "finishReason": "STOP"}]})
        if self.path.endswith("/chat/completions"):
            return self.respond(200, {"choices": [{"message": {"role": "assistant", "content": chat_reply(body)}, "finish_reason": "stop"}]})
        self.respond(404, {"error": "unknown path"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8103
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
