# Master run: implement the whole approved backlog before the first build

The owner approved the design mock (docs/design-mock/) and wants everything implemented in the app now, before the
Android build and deployment phases. You are fully autonomous. Ask nothing unless a blocker only the owner can solve
(an account login, a missing key you cannot work around, a legal or product decision). NEVER read, print or commit
backend/.env or frontend/.env, or any key.

## Order (each file has its own rules, loop and finish steps; follow them)
1. docs/LOGGING_PROMPT.md  - user-driven logging, big food and drink catalogue, photo snap, kitchen from a big list
2. docs/DESIGN_PROMPT.md   - design system, responsive phone and PC layouts, every screen, Telugu and English, dark mode
3. docs/INSIGHTS_PROMPT.md - KPIs, habit score, best and worst day, patterns, shareable weekly card
4. docs/EXTRAS_PROMPT.md   - illustrated food images, voice logging, barcode, water and reminders, challenges, regional
                             modes, workout library, progress photos
5. Final pass: full pytest once (-n 0, nothing else running), then the full Playwright run alone, fix failures in their own
   PRs, make sure `npx expo-doctor` is 20/20, tsc and ESLint are clean, the web build works, and the Privacy Policy, Terms
   and docs/PLAY_DATA_SAFETY.md match what the app now collects and sends. Write one "Master run summary" at the top of
   docs/PROGRESS.md: what shipped, what is verified, what is not, and a single checklist of everything the owner must do
   (keys, accounts, Telugu review, nutritionist and legal review, phone checks).

## Rules for a very long run
- Resume protocol: keep a "Master run status" checklist at the top of docs/PROGRESS.md (one line per item, with PR
  numbers). Update and merge it after every item. If your context fills up or the session restarts, `git pull`, read that
  checklist and continue from the first unchecked item. Never redo merged work.
- One branch and PR per item, squash-merge when green, no stacked branches, never force-push main.
- Memory discipline (the PC runs low on memory): never run the backend suite, Playwright and Expo at the same time. Run
  only the relevant test files while iterating. Stop Expo before the full pytest run, and the backend before the Playwright
  run only if it is not needed. If a process is killed for low memory, wait, retry once, then continue with the next item and
  note it in PROGRESS.md.
- External services are always behind provider interfaces with fakes in tests. Real Gemini quota is limited: use the fake
  in tests and make at most a few real calls per run for smoke tests (VISION_PROVIDER=auto falls back to Groq).
- Telugu: write natural, simple wording; list uncertain strings in PROGRESS.md for a native reader.
- Honest health language everywhere: wellness guidance, estimates labelled, no medical claims.
- If a feature cannot be verified without the installed app, build it with graceful fallback and say so.
- At the end of each of the four runs, post a short summary: files changed, tests added, what to verify on the phone.
