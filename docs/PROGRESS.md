# Phase 1 progress (2026-10-19)

All nine Phase 1 fixes from docs/PHASE1_PROMPT.md are merged to main, one squash-merged PR each:
#1 plan day, #3 Google-account login, #4 timezone, #5 correctable logs, #6 fallback calories,
#7 AI busy, #8 prompt quote, #9 activity duration, #10 Today's progress. #2 is an accidental empty
duplicate of #1, left in place because main's history is never rewritten.
New regression tests live in `backend/tests/test_phase1_fixes.py` (29 tests). Each run signs up a
throwaway user, so results don't depend on the shared preview account, and deletes it afterwards.

## What changed

| Fix | What changed | Files | Tests added |
|---|-----|-------|-------------|
| 1 | Plan advances by calendar day: `today_index` = days since the plan started, wrapped within 7. Used by Today, Plan (preselects and labels today's day) and `/eat-now`. | server.py, (tabs)/index.tsx, (tabs)/plan.tsx, types.ts | TestPlanDayIndex (3) |
| 2 | Email login to a Google-created account (empty or invalid password hash) gives a clean 401 instead of a 500. | server.py | TestGoogleAccountLogin (3) |
| 3 | "Today" uses the profile `timezone` (default Asia/Kolkata; unknown values fall back to it). Covers log dates, dashboard, eat-now, plan day and age, the plan's one-week window and the health summary. Onboarding sends the device timezone. | server.py, onboarding.tsx, src/lib/timezone.ts, test_iteration8 health test | TestUserTimezone (5) |
| 4 | `DELETE /meals/{id}`, `/activities/{id}`, `/weight/{id}` and `PATCH /meals/{id}`, all owner-scoped (404 otherwise). Today's plan meals come back `logged: true`, worked out from today's log. Logging the same plan meal twice in a day returns 409. UI: a check mark replaces "+", and Today lists logged meals and activities with Remove buttons. | server.py, ui.tsx, (tabs)/index.tsx, (tabs)/plan.tsx, api.ts, types.ts, styles.ts, i18n.ts | TestCorrectableLogs (5) |
| 5 | Fallback meals are sized from the user's calorie target (shared `calorie_target`): each meal type's share of the day, a small per-day swing, and goal-based macros. | server.py | TestFallbackCalories (3) |
| 6 | Groq 429/503 is retried with backoff (1 s, 2 s; at most 2 retries). After that, `/coach` and `/plan/regenerate` return 503 `{"detail": {"code": "ai_busy", "message"}}`. No canned coach replies. GET /plan keeps the old plan (or an unsaved starter plan) and flags it with `ai_status`. The app shows "AI is busy, try again in a minute" in Coach and Plan. New optional env var `GROQ_BASE_URL`. | server.py, .env.example, api.ts, (tabs)/coach.tsx, (tabs)/plan.tsx, types.ts, i18n.ts | TestAIBusy (6): runs a real second backend against a local fake Groq |
| 7 | Plan prompt schema quote fixed (`"fat_g": number`). | server.py | TestPlanPrompt (1) |
| 8 | Walk/strength calories = MET × 3.5 × weight / 200 × minutes (walking 3.5, strength 5.0). Weight comes from the latest log, then the profile, then 70 kg. Walking distance is estimated at 4.8 km/h. Today has a 10/20/30/45 min picker. | server.py, (tabs)/index.tsx, styles.ts | TestActivityEstimate (2) |
| 9 | The "readiness" score is gone. The dashboard returns `target_calories` and `activity_minutes`, and the card is now "Today's progress" (logged kcal / target, active minutes, "not a health measurement"). | server.py, today-progress-card.tsx (replaces readiness-card.tsx), (tabs)/index.tsx, types.ts, i18n.ts, two iteration-6/7 dashboard assertions | TestTodayProgress (1) |

## What is verified (on the PC)

- tsc: 0 errors. ESLint on `app` and `src`: 0 errors, the 2 known `require()` warnings.
  `scripts/cmd-guard` (Emergent leftover) still has its own pre-existing lint errors; I didn't touch it.
- `expo export --platform web` bundles every screen after each UI change.
- Full backend suite, run once at the end: 62 passed, plus the 3 known photo-recognition failures
  (no vision model). `test_stale_plan_auto_regenerates` hit a real Groq 429 on the first run.
  The new code kept the old plan as designed, and the test passed on its one retry a minute later.
- Endpoints hit for real: the plan day index on the preview account's real plan, and the login 401.
  A no-key backend produced varied fallback calories. A real Groq plan generation passed with the
  fixed prompt. The ai_busy path ran end to end against the fake provider.

## Not done or not covered (decide later)

- No UI to edit a meal (PATCH exists) or delete a weight entry (DELETE exists). The Progress screen
  could get one.
- The `logged` flag is worked out per request from today's log rather than saved on the plan. Only
  today's plan day is flagged.
- `GROQ_BASE_URL` is new and optional; production needs no change.
- Running locally: `uvicorn --reload` hangs on reload on this Windows machine. Restart the backend by
  hand after server.py changes.

## Please check on the phone (Expo Go)

1. **Plan day**: Today shows today's plan day, not Day 1. On the Plan tab, today's chip reads
   "Day N · Today" and is preselected.
2. **Timezone**: log a snack after midnight IST. It should count toward the new day on Today.
   (Existing accounts get Asia/Kolkata. A new onboarding stores the phone's timezone.)
3. **Logged meals**: tap "+" on a plan meal. It turns into a green check on Today and Plan, and
   tapping again can't double-log it. Under "Logged today", Remove deletes it, the "+" comes back,
   and the kcal total drops.
4. **Activities**: pick 10/20/30/45 min and tap Walk or Strength. The logged entry shows those
   minutes and a calorie estimate that changes with duration. Remove works.
5. **Today's progress card**: shows "X / target kcal" and active minutes. No more "/ 100" score.
6. **AI busy**: hard to trigger on purpose. If Groq is rate-limited, Coach should show a red
   "AI is busy, try again in a minute" line, not a coach reply. Plan refresh should show the same
   message and keep the current plan.
7. **Google account + password**: on the welcome screen, sign in with the Google account's email and
   any password. You should see "Email or password is incorrect", not a crash or a spinner.
8. **Telugu**: switch language and check the new strings (Logged today, Remove, Today's progress,
   AI busy).


# Phase 2 progress (2026-10-19): backend hardening

All eight Phase 2 items are merged to main as squash-merged PRs (one branch per item, each based on
main), plus two bug-fix PRs the full test run turned up. New tests are in
`backend/tests/test_phase2_hardening.py` (37 tests; same throwaway-user approach as Phase 1).

## What changed

| Item | PR | What changed | Tests |
|------|----|--------------|-------|
| 1. MongoDB indexes | #12 | `ensure_indexes()` runs at startup (idempotent): unique `users.email` and `users.id`; `(user_id, date)` and `(user_id, created_at)` on meals, activities, weights, coach_messages; `(user_id, updated_at)` on plans; `(user_id, start)` on health_records; a TTL index on `user_sessions.expires_at`. Duplicate emails already in the data are logged and a plain index is created instead, with no deletion (neither dev DB had any). The signup race is caught as `DuplicateKeyError` and returns 409. Sessions store `expires_at` as a date so the TTL applies; legacy string values are converted at startup. | TestIndexes (8), including 6 concurrent signups giving 1 account |
| 2. Login protection | #13 | `/auth/login` and `/auth/signup`: 10 attempts per 15 min per IP and per email, then 429 with a clear message and `Retry-After`. In-memory, behind `SlidingWindowLimiter` (`record`/`reset`). Loopback is exempt by default so local dev and the tests are never blocked. | TestAuthRateLimit (6) |
| 3. CORS allowlist | #14 | Origins come from `CORS_ORIGINS`; the default is the Expo web build (`localhost`/`127.0.0.1` on 8081 and 19006). Credentials are off (Bearer tokens). | TestCors (5) |
| 4. Lifespan handler | #12, #15 | `@app.on_event` replaced by a `lifespan` (it had to land with item 1). #15 adds the regression tests. | TestLifespan (3) |
| 5. Trimmed requirements | #16 | Removed boto3, requests-oauthlib, cryptography, passlib, python-jose, pandas, numpy, jq, typer, python-multipart, black, isort, flake8, mypy. | Verified in a fresh venv: backend runs, 87 tests collect, Phase 1+2 suites pass |
| 6. Plans capped at 5 per user | #17 | New plans are saved through `save_plan()`, which deletes older ones beyond the latest 5 and never the new one. The preview account went from 14 plans to 5. | TestPlanCap (3) |
| 7. Health conditions + disclaimer | #18 | Conditions are sent explicitly to the plan and coach prompts, framed as general wellness guidance (no diagnosis, no medicines, no "medically tailored"). A server-side guard replaces plan reasoning or day focus that names a user's condition. Coach and Plan show a disclaimer in English and Telugu. | TestHealthConditions (5) |
| 8. UI gaps | #19 | Edit button on logged meals (inline form, `PATCH /meals/{id}`); a "Weight entries" card on Progress with Remove (`DELETE /weight/{id}`). English and Telugu. | TestProgressEditDelete (3) |
| Bug: coach history | #20 | History and AI context read the **oldest** messages (ascending sort with a cap), so long chats stopped showing anything new. Now the newest are fetched and reversed. | TestCoachHistoryRecency (2) |
| Bug: empty AI replies | #21 | The reasoning model sometimes returns an empty reply; it is now retried like a rate limit, and the coach's token limit goes 1200 to 2000. | TestEmptyAiReply (2) |

## What is verified (on the PC)

- tsc: 0 errors. ESLint on `app` and `src`: 0 errors, the 2 known `require()` warnings. The web export
  bundles every screen after each UI change.
- Full backend suite run on main: 91 passed, 7 failed. Three were the known photo-recognition
  failures. The other four were real problems that led to #20 and #21 (two coach tests hit the empty
  reply, one hit the oldest-messages bug, and the stale-plan test was rate-limited by Groq and passes
  on its own). After those fixes each passes when re-run on its own. I did not run the whole suite a
  second time, because of Groq 429s; the final merged code differs from the tested code only by #20 and #21.
- Endpoints hit for real: 11 logins via the PC's LAN IP gave 10 x 401 and then 429; a CORS preflight
  from `http://localhost:8081` was allowed; a user with PCOS and diabetes got a real Groq plan whose
  reasoning no longer names either condition.

## Things you should know

- **Production settings.** `AUTH_RATE_LIMIT_EXEMPT_IPS` defaults to loopback so dev is never blocked;
  set it to empty when deploying. Behind Render's proxy also set `TRUST_PROXY_HEADERS=1`, or every
  user will share the proxy's IP. Set `CORS_ORIGINS` to the deployed web origin if you ship a web build.
  All of these are documented in `backend/.env.example`; I did not touch the real `.env`.
- **The rate limiter is per process and in memory.** It resets when the backend restarts and doesn't
  work across several instances. Move `SlidingWindowLimiter` to Redis or Mongo before scaling out.
- **Web build over the LAN.** If you open the Expo web build at `http://<PC IP>:8081`, add that origin
  to `CORS_ORIGINS`. The phone app is not affected by CORS.
- **Health-condition limits.** The server guard only checks the plan reasoning and day focus, not meal
  names, and the coach can still make soft claims such as "keeps blood sugar steady". That is why the
  disclaimer is always visible.
- **Existing sessions.** Google-login sessions stored before this change are converted at startup.
- **Memory.** The backend process I had started was stopped once by Claude Code because the PC was
  low on memory. Start it again when needed.

## Please check on the phone

1. **Sign in/out and sign up** still work (indexes and the session change are invisible when correct).
2. **Wrong password 11 times** from the phone: you should see "Too many attempts. Please wait 15 minutes
   and try again." (Your phone is not loopback, so the limit applies; restarting the backend clears it.)
3. **Coach and Plan** show the new "general wellness guidance, not medical advice" notice, and it is in
   Telugu when you switch language.
4. **Onboarding with a condition** (for example "PCOS"), then refresh the plan: the Nutrition note should
   not mention the condition.
5. **Today, logged meals**: tap Edit, change calories, Save. The row and the total update. An empty name
   or a letter in a number gives an error. Remove still works.
6. **Progress**: log two weights, then Remove one under "Weight entries".
7. **Long Coach chat**: after many messages, reopening Coach shows the latest ones, not the first.
8. **Coach in general**: it should rarely say "AI is unavailable" now; if Groq is rate-limited you still
   get "AI is busy, try again in a minute".
