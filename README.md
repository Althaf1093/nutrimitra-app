# Wellstride

A premium, privacy-first AI wellness companion for India, in English and Telugu. Wellstride builds an adaptive 7-day food and movement plan from your profile and goals, helps you log meals (including by photo), tracks activity and weight trends, and gives day-to-day guidance through an AI coach — without medical diagnosis or unrealistic promises.

## Features

- **AI health coach** — conversational guidance with persisted history and safety framing
- **Food-photo recognition** — snap a meal, get a suggested log entry with editable alternatives
- **Adaptive 7-day plans** — regenerated from what you actually log (meals, activity, weight trend)
- **Google Sign-In**
- **Health device sync** — HealthKit (iOS) / Health Connect (Android), permission-gated
- **Reminders** — meals, hydration, movement, weekly review (on-device notifications)
- **Bilingual** — English and Telugu, including a bundled Telugu font for correct glyph shaping
- **Recipes** — structured recipe cards from the coach, one-tap "log as meal"

## Stack

- **Frontend:** Expo SDK 57 / React Native, `expo-router` (file-based routing), TypeScript
- **Backend:** FastAPI (Python), MongoDB
- **AI:** Groq (`openai/gpt-oss-120b`) for the coach and plans; Google Gemini Flash for food-photo recognition

## Getting started

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in MONGO_URL, JWT_SECRET, GROQ_API_KEY
uvicorn server:app --reload --port 8001
```

### Frontend

```bash
cd frontend
yarn install
yarn start
```

Scan the QR code with Expo Go to run on a device, or press `w` for web.

### Food-photo recognition (add your Gemini key)

Photo logging uses Google Gemini Flash. It stays switched off, and the app says so, until you add a key:

1. Create a free key in [Google AI Studio](https://aistudio.google.com/apikey).
2. Open `backend/.env` yourself and set `GEMINI_API_KEY=` to your key. Never commit this file or paste the key anywhere else.
3. Restart the backend. `GET /api/` then shows `"configured": true` for Gemini under `vision`.

Optional settings in `backend/.env` (see `.env.example`):

- `GEMINI_MODEL` defaults to the current Flash model from Google's docs (`gemini-3.8-flash`). Change it if Google retires that id.
- `VISION_PROVIDER` is `gemini` (default), `groq`, or `auto` (Gemini first, then Groq). Groq vision is an optional secondary: it uses your existing `GROQ_API_KEY` and `GROQ_VISION_MODEL` (default `qwen/qwen3.8-27b`).

Providers live in `backend/vision.py` behind a small interface, so another provider can be added without touching the endpoint. Tests use a local fake provider and need no key.

## Project structure

```
backend/    FastAPI app (single server.py), pytest suite in tests/
frontend/   Expo Router app — app/ (routes), src/ (shared lib/context/components)
memory/     Living product record (PRD.md) — problem statement, architecture, build log, backlog
tests/      Top-level test scaffolding
```

## Status

Actively developed. See [`memory/PRD.md`](memory/PRD.md) for the full build history and prioritized backlog. Known gaps: Google Sign-In and native health adapters are code-complete but not yet verified on a physical device/build; UI componentization is still shallow in places.
