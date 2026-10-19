# End-to-end browser test run (do this AFTER Phase 3 is merged)

Read CLAUDE.md, docs/HANDOFF.md and docs/PROGRESS.md. You are fully autonomous. The goal: prove the app works
end to end in a real browser, and fix whatever breaks. Today only the API and a web-bundle build were checked; nobody
has clicked through the UI. A user just saw "Failed to fetch" on the onboarding screen.

## Setup (do it yourself)
- docker start nutrimitra-mongo; start the backend on 8001 (logs to a file) and the Expo web build on a free port.
- Use Playwright (install it as a dev dependency in a new `e2e/` folder, not in the app's dependencies) driving
  Chromium against the web build. Use a phone-sized viewport (390x844) and also one desktop pass.
- Use throwaway users created through the real sign-up screen and delete them afterwards. For AI calls use the
  existing fake-provider approach from the backend tests (GROQ_BASE_URL / the fake Gemini server) so runs are
  deterministic and never hit real rate limits. Never read or print .env or any key.
- Make sure CORS_ORIGINS in the test run allows the origin you use; if the default allowlist breaks a normal
  localhost workflow, fix the default or document it in README, with a clear error in the browser console.

## Flows to cover (one test per flow, with screenshots saved under e2e/screenshots, git-ignored)
1. Sign up with a new email and password; sign out; sign in again; wrong password shows the friendly message.
2. Onboarding (all 3 steps), including the 18+ rule, then landing on Today.
3. Plan tab: today's plan day is preselected; refresh plan; AI-busy message appears when the fake provider rate-limits.
4. Today: log a plan meal (check mark appears, cannot double-log), edit it, remove it, calories update.
5. Activity: pick a duration, log walk and strength, calories scale with minutes, remove one.
6. Progress: log a weight, see it in the chart, delete it.
7. Coach: send a message, see a reply; with the fake provider failing, see the "AI is busy" message.
8. Photo logging: upload a test image, see the confirm form, save it as a meal (fake vision provider).
9. Settings: switch to Telugu and back, privacy toggles, reminders, sign out. Check no raw i18n keys or hard-coded
   English remain on the main screens in Telugu.
10. Rate limit: 11 wrong logins show the "Too many attempts" message and a valid user can still log in later.

## Rules
- For every failure or console error / failed network request, find the root cause, fix it, add a regression test,
  and re-run until all flows pass. One branch and one PR per fix, squash-merge when green, no stacked branches.
- Add an npm script (`yarn e2e` or equivalent) and a short e2e/README.md explaining how to run it on Windows.
- Add the e2e results (flows passed, bugs found and fixed, screenshots list) to docs/PROGRESS.md, merge, and stop.
