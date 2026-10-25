# Welcome screen fixes (from Althaf's self-test of PR #63)

Do this as a small branch `fix/welcome-polish` + PR, right after the current Design item finishes (do not abandon work in progress).
Reference: docs/design-mock/Welcome.dc.html. Then tick the box in docs/PROGRESS.md "Pending fixes".

1. English mode shows "Your kitchen. Your goal." as headline AND as the green line. Make the headline and the subtitle different
   lines, as in the mock (Telugu headline, English tagline "Your kitchen. Your goal. Your stride." in green). In English mode show
   the English headline and the Telugu line should not appear unless the language is Telugu.
2. Default language: use the device language; if it is not Telugu or English, default to Telugu for India locale, else English.
   Remember the choice on device after the user picks.
3. Add the large "Get started" and "I have an account" buttons from the mock (phone). Get started opens create account,
   the other opens sign in. On desktop the two-column layout may keep the inline form; explain the choice in the PR.
4. Add spacing above "Forgot password?" (it touches the Sign in button on desktop).
5. Never apply letterSpacing (or negative tracking) to Telugu text anywhere in the app; it breaks conjunct letters
   (app/welcome.tsx line ~54 has letterSpacing -0.4). Make a helper in src/theme.ts that drops letterSpacing when language is te.
   Check Telugu renders with natural spacing in a Playwright screenshot at 390x844 and 1440x900.
6. Add or update a test for each fix. tsc, ESLint, relevant tests, squash-merge, pull main, post the short summary.
