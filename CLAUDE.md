# NutriMitra: Claude Code guide

Read docs/HANDOFF.md first. GitHub repo is the source of truth.

## Run (Windows)
- Docker Desktop running, then: docker start nutrimitra-mongo
- Backend: cd backend; .venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8001
- Frontend: cd frontend; CI=1 npx expo start --web   (CI=1 is required)
- Spinner hang = PC LAN IP changed: update EXPO_PUBLIC_BACKEND_URL in frontend/.env, restart Expo
- Tests: set EXPO_PUBLIC_BACKEND_URL=http://localhost:8001
  .venv\Scripts\python.exe -m pytest tests/ -n 0 --ignore=tests/make_test_image.py
  Tests hit a live server and Groq. Do NOT run the full suite back to back (429s).
  Known: 3 photo-recognition tests fail (no vision model). Not a regression.

## Rules
- One branch per fix, one PR per branch. Branch names: fix/<short-name>
- Before every commit: tsc, ESLint, pytest (only the relevant test files while iterating)
- Add or update a test for every fix
- Commits end with the Co-Authored-By trailer
- NEVER read, print or commit backend/.env or frontend/.env, or any key
- Don't touch Emergent leftovers or branding yet (Phase 3)
