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
