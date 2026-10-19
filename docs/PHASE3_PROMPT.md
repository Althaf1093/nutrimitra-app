# Phase 3: autonomous identity, cleanup and vision run

Read CLAUDE.md, docs/HANDOFF.md and docs/PROGRESS.md. Phases 1 and 2 are merged. You are fully autonomous:
do Phase 3 (items 1-8 below) end to end without asking me anything unless you hit a blocker only I can solve
(a missing key, an account login, a product decision). `gh` is already signed in.

## Decisions already made (do not re-ask)
- App display name: **Wellstride**
- Package / bundle ID (Android package and iOS bundleIdentifier): `in.inkbrief.wellstride`
- URL scheme and slug: `wellstride`
- Launch Android first; keep the iOS config valid but do not spend time on iOS-specific work.
- Vision provider: **Groq vision first, Gemini Flash as fallback**, behind a provider interface so it can be swapped later.
- Age rule: **18 and over** for the whole app (no minors).
- Icon: generate a simple **placeholder** (see item 3); a designer will replace it later.
- Theme colors: green #4A6B5D on cream #FDFBF7.
- Keep the repo name `nutrimitra-app` for now; do not rename the GitHub repo.

## Working loop for EACH item
1. Branch from up-to-date main (fix/ or feat/<name>). Merge each PR before starting the next; no stacked branches.
2. Implement it and add or update tests (backend/tests/test_phase3_*.py for backend behaviour).
3. Start what you need yourself (docker start nutrimitra-mongo, backend on 8001 with logs to a file, web build when UI
   changes). Read the logs. Run tsc, ESLint and the relevant pytest files. If anything fails, find the root cause,
   fix it, re-run. Do not weaken tests.
4. Verify for real: hit endpoints with curl or a script, and confirm `expo export --platform web` still bundles.
5. Open the PR, squash-merge when green, pull main, next item.

Do not run the full pytest suite more than once at the end (Groq 429s). When all items are merged, add a Phase 3
section to docs/PROGRESS.md (what changed, what is verified, what I must check on the phone), merge it, and stop.
NEVER read, print or commit backend/.env or frontend/.env. Never put a key in any file.

## Items, in this order

1. **Identity.** In frontend/app.json set name "Wellstride", slug "wellstride", scheme "wellstride", ios
   bundleIdentifier and android package `in.inkbrief.wellstride`. Replace every user-visible "NutriMitra" (app
   screens, i18n strings in both languages, backend GET /api/ status text, README title) with "Wellstride". Keep
   internal identifiers that don't affect users (repo name, DB name `nutrimitra`, collection names) unchanged.
   Make sure the Expo web build, `expo export` and the tests still pass. Update CLAUDE.md and docs if they name the app.

2. **Emergent cleanup.** Remove .emergent/, test_reports/, test_result.md, image_testing.md and the repo-level
   .gitconfig (it sets an Emergent git identity). Remove the `preinstall` cmd-guard hook from frontend/package.json
   and delete frontend/scripts/cmd-guard*. Confirm nothing imports them (grep first), then confirm a clean
   `yarn install` and the web build still work. Remove the Emergent Google-login code path ONLY in item 6, not here.
   Leave memory/PRD.md and design_guidelines.json in place.

3. **Placeholder branding assets.** Generate with a small script (Python Pillow or an SVG rendered to PNG; commit the
   script under frontend/scripts/make-icons.* so it can be re-run): a simple mark on #4A6B5D with cream details, such
   as two stylised footsteps or an upward path forming a "W"; no text and no third-party logos or fonts that need a
   licence. Produce: icon.png 1024x1024, adaptive-icon.png (foreground on transparent, safe zone respected),
   splash-image.png (mark on #FDFBF7 or #4A6B5D), favicon.png 48x48 and a 512x512 store icon at
   frontend/assets/store/icon-512.png. Set the adaptiveIcon backgroundColor and splash backgroundColor to match the
   theme (not #000000). Delete unused template images (partial-react-logo.png, react-logo*.png, app-image.png) after
   confirming nothing references them. Look at the generated images yourself and fix anything that looks wrong.

4. **Age gate (18+).** Backend: reject profile creation/update with age < 18 (422 with a clear message) and make the
   birth/age validation consistent. Frontend onboarding: enforce 18+ with a friendly message in English and Telugu;
   the lowest selectable age is 18. Add a one-line note on the welcome or onboarding screen. Add tests, including
   that existing adult profiles keep working.

5. **Vision provider.** Create a provider interface in backend/server.py (or a small backend/vision.py) with two
   implementations, tried in this order: (a) **Groq vision** first, because Groq's docs (console.groq.com/docs/vision)
   list a non-preview vision model (`qwen/qwen3.8-27b` at the time of writing; up to 3 images, ~2,048 tokens per
   image). Check why `pick_vision_model` previously found no vision model: its matching is probably outdated and
   should accept the documented model ids; make the id configurable via GROQ_VISION_MODEL, and verify against the
   real Groq API through the backend itself (without reading or printing any .env or key). (b) **Gemini Flash** as the
   fallback or alternative, config via GEMINI_API_KEY (optional) and GEMINI_MODEL (default: look up the current
   Gemini Flash model id in Google's official docs using WebSearch/WebFetch; do not guess). A VISION_PROVIDER env
   (groq | gemini | auto, default auto) selects the order. Remove the Emergent vision package dependency. If no provider is configured, POST /coach/vision returns a clear 503 with a helpful message
   (no crash, no 502). Never log image bytes. Add GEMINI_API_KEY and GEMINI_MODEL to backend/.env.example (placeholder
   values only). Tests must NOT need a real key: use a local fake Gemini server like the fake Groq already used in
   the Phase 1 tests. Document in README how I add my key (I will paste it into backend/.env myself).
   The 3 known photo-recognition tests should pass against the fake provider or be updated to use it.

6. **Own Google sign-in groundwork.** Replace the Emergent-hosted Google login with Google's own OAuth: backend
   verifies a Google ID token (google-auth library) against GOOGLE_CLIENT_ID(S) from env; the app uses
   expo-auth-session (or the current recommended Expo approach, check the docs) to get the ID token. Keep existing
   Google-created accounts working (match on email). Add the env vars to .env.example. Because I cannot create the
   Google Cloud credentials until later, build it so that when GOOGLE_CLIENT_ID is not set the Google button is
   hidden and email login works normally. Test the backend verification path with a fake token verifier. Remove
   the Emergent session/verification code only after the new path is in place and tested.

7. **i18n sweep.** Find user-visible hard-coded English strings (settings labels, coach quick prompts, "Day N",
   "Back", etc. per docs/HANDOFF.md) and move them into src/i18n.ts with English and Telugu values. Telugu must be
   natural, simple wording; when unsure of a translation, keep a clear English fallback and list those keys in
   docs/PROGRESS.md for me to review. Do not change behaviour.

8. **Housekeeping.** Remove `LogBox.ignoreAllLogs(true)`; fix any warnings that surface that are real problems and
   list the rest. Remove packages that are clearly unused after grepping (candidates from the report: date-fns,
   dayjs, expo-blur, expo-haptics, expo-linear-gradient, react-native-dotenv, react-native-webview, and
   @tanstack/react-query and its provider if still unused); check peer dependencies and `expo-doctor` before removing
   anything, and keep what Expo or a plugin needs. Run tsc, ESLint and the web build afterwards.

After each PR, note: files changed, tests added, and what I should verify on the phone.
