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


# Phase 3 progress (2026-10-19): identity, cleanup and vision

All eight Phase 3 items are merged to main (one PR each, no stacked branches), plus one test-isolation fix.
New tests: `test_phase3_identity.py`, `test_phase3_age.py`, `test_phase3_vision.py`, `test_phase3_google.py`,
`test_phase3_i18n.py` and `test_phase3_housekeeping.py` (about 100 tests), plus shared fakes in `tests/fakes.py`
and `tests/conftest.py`.

## What changed

| Item | PR | What changed |
|------|----|--------------|
| 1. Identity | #23 | The app is **Wellstride**: `app.json` name, slug and scheme `wellstride`, iOS bundle ID and Android package `in.inkbrief.wellstride`; every user-visible "NutriMitra" is renamed (screens, both languages, API status and title, AI prompts, README, CLAUDE.md). The repo, the `nutrimitra` database and the on-device keys (`nutrimitra.session.token`, `nutrimitra.lang`) are unchanged on purpose, because renaming the keys would sign everyone out. |
| 2. Emergent cleanup | #24 | Deleted `.emergent/`, `test_reports/`, `test_result.md`, `image_testing.md`, the repo `.gitconfig`, the `preinstall` cmd-guard hook and `frontend/scripts/cmd-guard*`, `install-guard.sh`, `sync-shims.sh`. A clean `yarn install` works without them. |
| 3. Placeholder branding | #25 | `frontend/scripts/make-icons.py` (re-runnable, Pillow) draws a "W" path mark and writes `icon.png`, `adaptive-icon.png` (inside Android's safe zone), `splash-image.png`, `favicon.png` and `assets/store/icon-512.png`. Adaptive-icon background `#4A6B5D`, splash background `#FDFBF7`. Unused template images deleted. I looked at every image and redrew the first draft. |
| 4. 18+ | #26 | Profiles accept 18 to 100 (422 "You must be 18 or older to use Wellstride."). Onboarding checks the age, in English and Telugu, with a one-line note. A stored profile under 18 goes back through onboarding. No under-18 profiles exist in the local databases. |
| 5. Vision provider | #27 | `backend/vision.py`: Gemini Flash default (`gemini-3.8-flash`, the id in Google's docs, via `generateContent`), Groq vision optional (`qwen/qwen3.8-27b`), `VISION_PROVIDER` = gemini / groq / auto. No provider set up gives a clear 503; unusable answers give 503 (was 502). Image bytes and keys are never logged. The three photo tests now pass against a local fake. Emergent vision removed. |
| 6. Google sign-in | #28 | `POST /api/auth/google` verifies a Google ID token with `google-auth` (signature, audience from `GOOGLE_CLIENT_IDS`, issuer, expiry, nonce, verified email); accounts match on email, so old Google accounts keep working. The app uses `expo-auth-session`; the Google button is hidden unless `EXPO_PUBLIC_GOOGLE_CLIENT_ID` is set. The Emergent session code is gone. |
| 7. i18n sweep | #29 | About 100 keys moved into `src/i18n.ts` in English and Telugu: Settings, Coach prompts, "Day N", "Back", headings, placeholders, option labels and messages. Saved values stay English. |
| 8. Housekeeping | #30 | `LogBox.ignoreAllLogs(true)` removed. Removed `date-fns`, `dayjs`, `expo-blur`, `expo-haptics`, `expo-linear-gradient`, `react-native-dotenv`, `react-native-webview` and `@tanstack/react-query`. Kept `expo-linking` (a peer of `expo-router`). Aligned Expo patch versions and pinned one `react-native-screens`: `expo-doctor` went from 18/20 to **20/20**. |
| Test fix | #31 | A conftest fixture restores `server.db` after tests that swap it (a Phase 2 test left a closed event loop that broke a later in-process test in a full run). |

## What is verified (on the PC)

- tsc: 0 errors. ESLint on `app` and `src`: 0 errors, the 2 known `require()` warnings. `expo export --platform web`
  bundles after every UI change; `expo-doctor` is 20/20; a clean `yarn install` succeeds.
- Full backend suite, run once on main after item 8: **203 passed, 2 failed**. All three photo-recognition tests now
  pass (the "known failures" are gone). The two failures were `test_coach` (a real Groq rate limit, passes alone) and the
  isolation bug fixed in #31.
- Real checks without reading or printing a key: Groq's account lists `qwen/qwen3.8-27b`, and a real photo through
  `POST /api/coach/vision` with `VISION_PROVIDER=groq` returned 200. With no Gemini key the default returns the clear 503.
  Google token verification is tested with genuine RSA signatures against a local fake of Google's certificate endpoint.

## Not verified, and what you need to do

1. **Gemini is untested against Google.** Paste your key into `backend/.env` yourself (`GEMINI_API_KEY=`), restart the backend, then
   try Photo. Until then photo logging says it isn't set up. Steps are in the README.
2. **Google sign-in needs your credentials** (a "Web application" OAuth client ID): set `GOOGLE_CLIENT_IDS` in `backend/.env` and
   `EXPO_PUBLIC_GOOGLE_CLIENT_ID` in `frontend/.env`, then `npx expo start --clear`. The button appears only when the app has the ID.
   The browser popup flow is untested. For the Android store build, Expo recommends `@react-native-google-signin/google-signin`
   (needs a development build, not Expo Go); the app side is isolated in `frontend/src/lib/google-auth.ts`. That is a Phase 5 task.
3. **Dependencies changed.** Run `yarn install` in `frontend` before starting Expo, then `npx expo start --clear`. Expo packages
   moved to the latest SDK 57 patch versions, so please run the app once on your phone.
4. **Telugu needs a native reader.** I wrote Telugu for every new key; these are the ones I am least sure of:
   `strengthWord`, `activeKcalNote`, `ringMoving`, `weightTrend`, `trendHint`, `privacyLine`, `planReasoningFallback`,
   `optEggetarian`, `optEnjoy`, `optBudgetFriendly`, `optBalanced`, `optFlexible`, `wellnessNotice`, `aiBusy`, `aiBusyPlan`,
   `ageMustBe18`, `googleFailed`. The older `photoDisclaimer` says "మీ యంత్రం" ("your machine"); "మీ పరికరం" ("your device") is probably meant.
5. **Backend text is still English** (the Eat-now reasoning and disclaimer, the Progress weekly review, API error messages). Translating
   it needs the backend to take a language, which is a behaviour change, so I left it.
6. **Warnings may appear on the phone.** `LogBox.ignoreAllLogs` is gone, so yellow warning boxes that used to be hidden can show up.
   Tell me which, and I will fix the real ones.

## Please check on the phone

1. Open the app: the name is Wellstride on the welcome screen, and you are still signed in.
2. New account, onboarding: age 17 is refused with the 18+ message (also in Telugu); 18 continues.
3. Settings, switch to Telugu, and look through Today, Plan, Coach, Progress, Settings, Eat now and Photo for leftover English.
4. Photo, once you add the Gemini key: take a picture, check the confirm form. Without the key you see "isn't set up yet" and can still log by hand.
5. Welcome screen without Google credentials: no Google button, and email sign-in works.
6. Everything else (Today, Plan, Coach, Progress) behaves as before. This checks the Expo package updates.

# End-to-end browser run (2026-10-19)

Playwright (in `e2e/`, not an app dependency) drives the Expo web build in Edge against a throwaway backend database with
a fake AI provider. See `e2e/README.md`; run with `npm run e2e` inside `e2e`.

## Result: 13 of 13 passed (3.0 min)
Phone: flows 1 (sign up, sign out, sign in, wrong password), 1b (unreachable backend is explained), 2 (onboarding and
18+), 3 (plan, AI busy), 4 (log, edit, remove a meal), 5 (activity), 6 (weight), 7 (coach, AI busy), 8 (photo logging),
9 (Telugu and back, privacy, reminders, sign out, no leftover English or raw keys), 10 (11 wrong logins, then a valid
user still gets in). Desktop pass: flows 1 and 4.

## Bugs found and fixed (one PR each)
- #33 Web build only worked from one origin: any localhost port is now allowed, and an unreachable backend gives a clear
  message instead of "Failed to fetch".
- #34 and #37 Needless `/me` request with no token, and stale navigation / signed-out requests after sign-out.
- #36 expo-notifications web warning (loaded on devices only).
- #35 A brittle no-token guard test.
- #38 Settings toggles overwrote saved preferences.
- #39 Telugu leftovers found by the browser scan.
- This PR: screenshots were all named `undefined-*` and overwrote each other; now `<flow>-<name>.png`.

## Screenshots (e2e/screenshots/phone, git-ignored)
welcome, today, wrong-password, back-in, step-2, step-3, under-18, plan, ai-busy (plan and coach), logged, editing,
three-activities, weight-logged, recipe, confirm, settings-english, settings-telugu, telugu-today/plan/coach/progress,
too-many-attempts, cannot-reach.

## Not covered
Real Gemini/Groq/Google calls (fakes only), and native phone behaviour: please still try the app on your phone.

# Phase 4 progress

## Photo self-test (2026-10-19)
Through the running backend only (`.env` not opened): a throwaway user posted `e2e/fixtures/meal.jpg` to `/api/coach/vision`.
- **Gemini (`gemini-3.8-flash`, the id Google's own error message recommends): the model id is right, but the key is not usable
  yet.** Google answered 503 "high demand" (also for `gemini-flash-latest`) and, in the browser run, 429 "You exceeded your
  current quota". `gemini-2.5-flash` is closed to new users and `gemini-3.8-flash-lite` does not exist. This is an account/quota
  matter for the owner: check the key's plan and quota in Google AI Studio (https://aistudio.google.com), or enable billing.
- **With `VISION_PROVIDER=auto` (Gemini, then Groq) it works today:** 200 with "Masala Rice", 320 kcal, macros, confidence, and
  `provider: groq`. The Playwright photo flow against the real providers also passed (`E2E_REAL_VISION=1`, see `e2e/README.md`).
- Fix shipped: the log line for a failing provider now includes the provider's own error message (never the image or the key),
  which is how the 503/429 above were diagnosed. Test: `test_phase4_vision_log.py`.
- **Do this:** set `VISION_PROVIDER=auto` in `backend/.env` so photo logging keeps working while Gemini is limited or busy.

# UX run (2026-10-20): toasts and smart food search

Three PRs, each merged to main: #50 toast, #51 food catalogue and search, #52 Log food screen. Plus #49 (the web build uses
`localhost` for the backend when the page is on `localhost`, so a changed LAN IP no longer breaks the browser).

## What changed
- **Toast (#50).** `src/components/toast.tsx`, `useToast().show(message, {type, actionLabel, onAction})`. A small light pill (max 420
  wide, centred) above the tab bar, check / info / "!" icon, soft shadow, fades in, goes away after 2.5 s (4 s for errors and for
  toasts with Undo), swipe or tap to dismiss, one at a time (a new one replaces the old), taps pass through, `role` status or alert
  and a native screen-reader announcement. Replaced the black bar on Today, the chip on Plan, the text on Coach; Progress now says
  when a weight is saved or removed. Undo after logging or removing a meal or activity. The `+` on a plan meal turns into the check at
  once (Today and Plan) and rolls back with an error toast if the API fails.
- **Food catalogue (#51).** `backend/data/foods.json`: 589 foods, Indian-first plus common global foods, with Telugu names, synonyms,
  default serving, kcal / protein / carbs / fat, and extra serving options. `GET /api/foods/search`, `/api/foods/recent`,
  `/api/foods/frequent` (sign-in required, rate limited per person, `FOODS_RATE_LIMIT`, default 120 a minute). Matching covers names,
  family terms ("egg", "dosa"), synonyms and Telugu names; plurals and typos ("dosaa", "omlet") are forgiven; ranking is match first,
  then popularity, then your recent foods. An empty query returns your recents. A logged meal can carry a serving text (`portion`).
- **Log food screen (#52).** One search box, suggestions as you type (200 ms), a one-tap `+` on every row, a bottom sheet for serving,
  quantity and meal slot (default by time of day), Recent / Frequent / category chips when empty, "No match. Add it yourself." with a
  custom food form, the photo path kept (Photo button here, and the Coach camera opens it directly). A failed search keeps the text and
  shows the error toast. `AppIcon` now falls back to a glyph on web and Android, where the SF Symbols drew nothing (icons were blank
  in the browser).

## What is verified (on the PC)
- tsc 0 errors, ESLint 0 errors (the 2 known `require()` warnings), `expo export --platform web` builds.
- Backend: 35 new tests in `backend/tests/test_ux_food_search.py`. Full suite once at the end against a freshly restarted backend:
  **324 passed, 4 failed**, then the 4 were fixed and `test_phase3_i18n.py` re-run (13 passed), so 328 of 328. Four i18n tests were failing for stale reasons and were fixed: two came from the Phase 4
  consent strings (an empty connector string is legitimate), one from `cm` / `ft` unit labels, one because the plan meal body moved to
  `src/lib/plan.ts`.
- Playwright: new `toast.spec.ts` (2) and `food.spec.ts` (8). Screenshots reviewed: the pill is small, light, centred above the tab bar
  and gone by itself; the sheet shows the totals changing with the quantity; Telugu renders. Full e2e once at the end: **29 passed, 1 skipped** (the real-photo
  spec, which needs real keys) and 1 failed: flow 13 (delete account) hit the test backend's limit of 10 sign-ups a minute, because the
  run now has more flows than that. `fixtures.ts` now waits when the last minute is nearly full; flows 11 to 13 and all `food` flows
  re-ran green back to back.

## Please check on the phone
1. Today and Plan: tap `+` on a meal. The check appears at once, a small pill shows briefly (not a black bar), Undo works.
2. Today: remove a meal and an activity, tap Undo. Coach: log a recipe, the pill sits above the chat box.
3. Log food: type egg, dosa, idli, a typo (dosaa). Tap `+` for the default serving; tap a row, change the quantity, pick a slot, Add.
4. The Photo button on that screen, and the camera on the Coach tab. Custom food from "Can't find it?".
5. Telugu mode on the Log food screen and in the toast.
6. Icons on Android and in the browser now show glyphs; check they look acceptable (they are plain text symbols, not the iOS icons).

## Needs human review
- **Nutrition values are estimates.** Every number in `foods.json` is a rounded estimate I wrote from general knowledge, not from a
  food composition table. A nutritionist should review them before launch (restaurant dishes and mixed dishes vary the most; alcohol and
  packaged items too). The app says "Nutrition values are estimates, not measurements." under the list and in the sheet.
- **Telugu food names.** I wrote a Telugu name for about 95% of the 589 foods; none have been read by a native speaker. Least sure:
  dishes with regional names (`Bobbatlu`, `Ariselu`, `Kajjikayalu`, `Punugulu`, `Mulakkada` / `Munagakaya` items, `Sunnundalu`, `Chekkalu`),
  borrowed words spelled in Telugu (`ఆమ్లెట్`, `శాండ్‌విచ్`, `బర్గర్`, `మష్రూమ్`), and the mixed Telugu-English dishes ("చికెన్ 65").
- **Telugu UI strings added in this run** (all new keys): `undo`, `undone`, `couldNotUndo`, `weightLogged`, `weightRemoved`,
  `couldNotSaveWeight`, `logFood`, `logFoodEyebrow`, `searchFoodPlaceholder`, `searchFoods`, `clearSearch`, `recentFoods`,
  `frequentFoods`, `popularFoods`, `browseFoods`, `catEggs`, `catDosa`, `catIdli`, `catRice`, `catDal`, `catCurry`, `catSnacks`,
  `catFruits`, `catDrinks`, `noMatchAddYourself`, `addCustomFood`, `addCustomTitle`, `searchFailed`, `servingLabel`, `quantityLabel`,
  `addToLog`, `addWord`, `estimateNote`, `backToSearch`, `totalLabel`. Least sure: `servingLabel` ("సర్వింగ్"), `quantityLabel`,
  `frequentFoods`, `noMatchAddYourself`, `addCustomFood`, `estimateNote`.
- `photo` now reads "Photo" / "ఫోటో" (it used to say "Log with photo"); the Today link is the new `logFood`.

## Not covered
Real Gemini / Groq calls (fakes only), native phone behaviour (keyboard, safe areas, the modal's toast host on iOS), and Android icon
rendering. The Undo for a removed plan meal re-creates it as a new entry (same day), so its time of logging changes.
