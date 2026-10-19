# Phase 4: self-test the photo feature, then store-mandatory features

Read CLAUDE.md, docs/HANDOFF.md and docs/PROGRESS.md. Phases 1-3 and the E2E suite are merged. You are fully
autonomous: do Step 0 and then items 1-6 end to end without asking me anything unless you hit a blocker only I can
solve (an account login, a product decision). `gh` is signed in.
NEVER read, print or commit backend/.env or frontend/.env, or any key. Never put a key in any file.

## Step 0. Self-test the Photo feature (before any new work)
I have pasted my own GEMINI_API_KEY into backend/.env. Do NOT open that file. Verify through the running backend only:
1. `git pull origin main`, `yarn install` in frontend, docker start nutrimitra-mongo, restart the backend (it only
   reads .env at startup) with logs to a file.
2. Sign up a throwaway user, finish onboarding via the API, then POST a real meal photo to /api/coach/vision
   (use a clear food image from tests/ or generate one; no people in it). Confirm a sensible food name, calories
   and macros come back, and that the log shows the provider used without printing image bytes or the key.
3. If it fails (model id, 404, quota, 503), diagnose from the backend logs, fix the root cause (for example set a
   working GEMINI_MODEL default in code or .env.example, never in .env), re-run until it works.
4. Run the Playwright Photo flow in e2e/ against the real provider once, and confirm the UI shows the result.
5. Add a short "Photo self-test" note to docs/PROGRESS.md. If a code fix was needed, ship it as its own PR first.

## Decisions already made (do not re-ask)
- App: Wellstride, 18+ only, Android first, health data and meal photos are sent to AI providers (Gemini, Groq).
- Policy documents are drafts, not legal advice; mark them "Draft for review" in docs/PROGRESS.md and tell me to
  have them reviewed before launch. Support email: use a placeholder constant SUPPORT_EMAIL read from env
  (default support@inkbrief.in) and list it in PROGRESS.md for me to confirm.
- Email sending: use a provider interface with a console/log implementation as default for dev and tests, and a
  Resend (free tier) implementation selected by RESEND_API_KEY and EMAIL_FROM env vars. Tests use the fake.

## Working loop for EACH item
Branch from up-to-date main (fix/ or feat/<name>), implement, add tests (backend/tests/test_phase4_*.py and an
E2E flow where UI changes), run tsc, ESLint and the relevant pytest files, verify with curl and the web build,
open the PR, squash-merge when green, pull main, next item. No stacked branches. Full pytest suite once at the end.

## Items, in this order
1. **Privacy Policy and Terms.** Write plain-language documents (English; Telugu summary optional) covering: what
   data is collected (account, profile, health conditions, weight, meals, activity, meal photos, coach messages),
   that meal photos and health details are sent to third-party AI providers (Google Gemini, Groq) to generate
   results, retention, in-app deletion, security, 18+ only, wellness guidance not medical advice, contact email,
   India DPDP-style rights (access, correction, deletion, grievance contact). Serve them from the backend as public
   HTML pages at /privacy and /terms (no login), and show them in the app (Settings and signup) with links.
   Add tests that the pages return 200 and contain key phrases.

2. **Consent at signup.** Add a required checkbox "I am 18 or over and agree to the Terms and Privacy Policy" to
   signup and Google sign-in first use. Backend stores consent_version and consent_at on the user and rejects
   signup without it (422). English and Telugu strings. Existing users are asked once on next launch.

3. **In-app account deletion** (Google Play requirement). Settings > Delete account with a clear confirmation
   (type DELETE or re-enter password; Google users confirm differently). Backend DELETE /api/account removes the
   user and ALL their data across every collection (meals, activities, weights, plans, coach_messages,
   health_records, sessions, etc.) and invalidates tokens. Test that nothing remains for that user_id.
   Also add a public web page /delete-account explaining how to request deletion (Play Console asks for a URL).

4. **Password reset.** POST /api/auth/forgot-password (always returns the same response, no email enumeration, rate
   limited) and POST /api/auth/reset-password with a single-use, hashed, time-limited (30 min) token. Email goes
   through the provider interface. App screens: "Forgot password?" on login, and a reset screen reachable by link
   or by entering the code. Test expiry, reuse and enumeration safety.

5. **Email verification.** Send a verification code at signup; unverified users can use the app but see a gentle
   banner, and password reset only works for verified emails. Resend endpoint rate limited. Google-created users
   count as verified. Test the flow with the fake email provider.

6. **Play Data Safety draft.** Write docs/PLAY_DATA_SAFETY.md: a table of every data type collected, purpose,
   whether shared with third parties (Gemini, Groq), whether optional, encryption in transit, deletion method,
   matching the real code. Also docs/PLAY_STORE_LISTING.md with a draft short description (80 chars), full
   description, category (Health & Fitness), content rating notes, and the health-app declaration answers.

## Finish
Add a Phase 4 section to docs/PROGRESS.md (what changed, what is verified, what I must do: confirm support email,
get policies reviewed, create a Resend account and key, check the screens on the phone). Merge it and stop.
After each PR, note: files changed, tests added, and what I should verify on the phone.
