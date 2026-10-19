# Phase 2: autonomous backend hardening run

Read CLAUDE.md, docs/HANDOFF.md and docs/PROGRESS.md. Phase 1 is merged. You are fully autonomous:
do Phase 2 (items 1-8 below) end to end without asking me anything unless you hit a blocker only I can
solve (a missing key, an account login, a product decision). `gh` is already signed in.

## Working loop for EACH item
1. Branch from up-to-date main: fix/<name> (do NOT stack branches this time; merge each PR before
   starting the next so every branch is based on main).
2. Implement it and add a test (backend/tests/test_phase2_hardening.py, same throwaway-user approach
   as test_phase1_fixes.py).
3. Start what you need yourself (docker start nutrimitra-mongo, backend on 8001 with logs to a file).
   Read the logs. Run the relevant pytest files. If anything fails, find the root cause, fix it,
   re-run. Do not weaken tests to make them pass.
4. Hit the real endpoint(s) with curl or a script to confirm the behavior.
5. Open the PR, squash-merge it when green, pull main, move to the next item.

Do not run the full pytest suite more than once at the end (Groq 429s). The 3 photo tests are known
failures. When all items are merged, update docs/PROGRESS.md with a Phase 2 section (what changed,
what is verified, what I must check), merge it, and stop.

## Items, in this order

1. MongoDB indexes, created at startup (idempotent, in the app lifespan):
   - unique index on users.email (normalize emails to lowercase on signup/login; handle the existing
     find-then-insert race by catching DuplicateKeyError and returning 409)
   - compound indexes (user_id, date/created_at) on meals, activities, weights, coach_messages,
     health_records, plans
   - TTL index on user_sessions expiry so expired sessions are removed
   If existing dev data has duplicate emails, report it and handle gracefully; do not delete data.

2. Login protection: rate limit /auth/login and /auth/signup (e.g. 10 attempts per 15 minutes per IP
   and per email, in-memory is fine for now, but isolate it behind a small function so it can move to
   Redis/Mongo later). Return 429 with a clear message. Make sure the test suite's own logins are
   not blocked.

3. CORS: replace allow-all with an allowlist from a CORS_ORIGINS env var (comma separated). Default
   for local dev must still allow http://localhost:8081 and http://localhost:19006 so the Expo web
   build keeps working. Add the variable to backend/.env.example (never touch the real .env).

4. Replace deprecated @app.on_event with a lifespan handler.

5. Trim backend/requirements.txt to what server.py and the tests actually import (the report lists
   pandas, numpy, boto3, passlib, python-jose, typer, jq and dev tools as unused). Verify by
   creating a fresh venv in the scratchpad, installing the trimmed file, and running the backend and
   the relevant tests there. Keep anything the tests need.

6. Cap db.plans growth: keep only the latest 5 plans per user (delete older ones after inserting a new
   one). Do it safely (never delete the plan just created).

7. Health conditions: include the user's stored health conditions in the plan-generation and coach
   context explicitly, and add a visible, plain-language disclaimer in the app (Coach and Plan
   screens, English and Telugu) that suggestions are general wellness guidance, not medical advice.
   Do not claim the plan is medically tailored. Add the strings to src/i18n.ts in both languages.

8. Small UI gaps from Phase 1: add an edit-meal action (uses PATCH /meals/{id}) and a delete button
   for weight entries on the Progress screen. Keep the style consistent with the existing screens and
   use i18n strings for any new text. Run tsc and ESLint; verify the web build compiles.

After each PR, note: files changed, tests added, and anything I should verify on the phone.
