# Phase 1: autonomous bug-fix run

Read CLAUDE.md and docs/HANDOFF.md. You are fully autonomous: do Phase 1 (fixes 1-9 below) end to end
without asking me anything unless you hit a blocker only I can solve (a missing key, an account login,
a product decision).

## Working loop for EACH fix
1. Branch fix/<name>. Implement the fix and add a test.
2. Start what you need yourself: docker start nutrimitra-mongo, the backend (uvicorn on 8001, in
   background, log to a file), and for UI changes the web build (CI=1 npx expo start --web).
   Read the logs yourself.
3. Run tsc, ESLint and the relevant pytest files. If anything fails or logs show errors, diagnose the
   root cause, fix it, and re-run. Repeat until green. Do not stop at the first error. Do not skip or
   weaken tests to make them pass.
4. Hit the real endpoints (curl or a small script) to confirm the behavior works, not just the unit tests.
5. Open the PR, merge it (squash) when green, pull main, move to the next fix.

Do not run the full pytest suite more than once at the end (Groq 429s). If a 429 breaks a test, wait and
retry that test once. The 3 photo-recognition tests are known failures.
When all 9 are merged, write docs/PROGRESS.md (what changed, what is verified, what I must check on the
phone), commit it, and stop.

## Fixes, in this order

1. Day-1 bug. frontend/app/(tabs)/index.tsx line ~90 uses plan?.days?.[0], and backend eat_now uses
   [:1]. Pick the plan day by the user's local weekday relative to the plan's creation date (day index =
   days since plan start, wrapped within the 7-day plan). Apply the same logic in /eat-now.

2. Google-account login 500. Users created via /auth/session have password_hash "" and bcrypt.checkpw
   raises ValueError. In /auth/login, return a clean 401 (same message as wrong password) when the hash
   is empty or invalid. Catch ValueError.

3. IST "today". Replace UTC date logic with the user's timezone. Add a timezone field to the profile
   (default "Asia/Kolkata"), use zoneinfo, and apply it in /dashboard, /eat-now and any "today" filter.

4. Correctable logs. Add DELETE /meals/{id}, /activities/{id}, /weight/{id} (scoped to the current user)
   and PATCH for meals. Set the plan meal "logged" flag when a plan meal is logged, and make the Today
   screen hide or disable "+" for logged meals. Add delete UI on the Today screen.

5. Fallback calories. portion_for() hard-codes 430 kcal / 24 g protein. Compute realistic values per meal
   type and calorie target so fallback meals vary.

6. Groq 429 handling. Add retry with exponential backoff (max 2 retries). If still failing, return a
   structured error (e.g. code "ai_busy") that the frontend shows as a friendly "AI is busy, try again in
   a minute" message in Coach and Plan. No silent canned replies.

7. Fix the missing quote in the plan prompt (server.py line ~274, "fat_g").

8. Walk/strength buttons: log calories from duration (minutes x a sensible per-minute estimate using the
   user's weight if available), and let the user choose duration.

9. Readiness score: remove the fabricated formula. Either remove the card or rename it to an honest
   "Today's progress" based on logged calories vs target and activity minutes. Do not present it as
   health data.

After each PR, note: files changed, tests added, and what I should verify manually on the phone.
