# NutriMitra: Claude Code guide

Read docs/HANDOFF.md first. The GitHub repo (Althaf1093/nutrimitra-app, branch main) is the source of truth.

## Run (Windows)
- Docker Desktop running, then: docker start nutrimitra-mongo
- Backend: cd backend; .venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8001
- Frontend: cd frontend; CI=1 npx expo start --web   (CI=1 is required)
- Spinner hang = PC LAN IP changed: update EXPO_PUBLIC_BACKEND_URL in frontend/.env, restart Expo
- Tests: set EXPO_PUBLIC_BACKEND_URL=http://localhost:8001
  .venv\Scripts\python.exe -m pytest tests/ -n 0 --ignore=tests/make_test_image.py
  Tests hit a live server and Groq. Do NOT run the full suite back to back (429s).
  Known: 3 photo-recognition tests fail (no vision model). Not a regression.

## Working agreement
- Autonomy: the owner has given full permission. Work branch -> PR -> merge to main on your own,
  without asking, once checks pass. Keep going through the phases in docs/HANDOFF.md section 9.
- One branch per fix, one PR per branch. Branch names: fix/<short-name> or feat/<short-name>
- Before every commit: tsc, ESLint, pytest (only the relevant test files while iterating;
  full suite once at the end of a phase)
- Add or update a test for every fix
- Merge with squash (gh pr merge --squash --delete-branch) after checks pass, then pull main
- Never force-push to main. Never rewrite history on main.
- Commits end with the Co-Authored-By trailer; PR descriptions end with the Claude Code footer
- NEVER read, print or commit backend/.env or frontend/.env, or any key or token
- Don't touch Emergent leftovers or branding until the owner has chosen the final app name,
  package ID and vision provider (Phase 3). Ask once, then proceed.
- After each merged PR, post a short summary: files changed, tests added, what to verify on the phone

## Phase order
Phase 1 bug fixes -> Phase 2 backend hardening -> Phase 3 identity/branding -> Phase 4 store-mandatory
features -> Phase 5 build and device testing -> Phase 6 deploy and launch. Details in the owner's plan.
