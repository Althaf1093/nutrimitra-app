# Extras run: everything useful that does not need a native build

Read CLAUDE.md, docs/PROGRESS.md, docs/FEATURE_BACKLOG.md and docs/design-mock/. Run after the Logging, Design and
Insights runs. You are fully autonomous; ask me nothing unless a blocker only I can solve. NEVER read, print or commit
backend/.env or frontend/.env. One branch and PR per item, tests for each item (pytest with fakes for every external
service, Playwright for UI), tsc, ESLint, web build, `npx expo-doctor` stays 20/20, review your own screenshots at phone
and desktop sizes in English and Telugu, squash-merge when green. Match docs/design-mock/ and the design system. Full
pytest and full e2e once at the end, one after the other, never together (low-memory PC). Every feature must degrade
gracefully on web and in Expo Go when a native module is missing.
Privacy: whenever a feature sends a new kind of data to a third party (voice, barcode lookups), update the Privacy
Policy page, docs/PLAY_DATA_SAFETY.md and the in-app consent wording in the same PR.

## Items, in this order
1. **Illustrated food images.** A FoodImage component with original illustrated tiles in the mock's style for 40+
   categories (dosa, idli, rice and dal, curry, roti and paratha, biryani, egg, chicken, fish, paneer, sabzi, salad, fruit,
   nuts, tea, coffee, juice, lassi, soft drink, beer, whisky, wine, sweets, snacks, soup, oats and cereal, sandwich,
   noodles, pizza, burger, and more), a generic fallback, and a slot for a real photo URL later. Use it in food search
   results, meal cards, plan cards, the add sheet and the share card. Write docs/IMAGE_SOURCES.md (all illustrations are
   original). No scraped photos.
2. **Voice logging (Telugu and English).** Mic button in the add sheet. Record up to 30 s (web: MediaRecorder, native:
   expo-av), send to POST /api/foods/parse-speech, which transcribes with the vision/LLM provider interface (Gemini audio
   input by default, fake in tests; language hint te / en / auto), then maps the transcript to catalogue items and
   servings ("2 idli and sambar", "రెండు ఇడ్లీ, సాంబార్") with Groq or Gemini text as fallback, returning candidates for the
   user to confirm. Never store audio or transcripts beyond the request; do not log audio bytes. Clear errors and a
   typed fallback. Tests with fake providers, including Telugu phrases.
3. **Barcode scan.** expo-camera barcode scanner (web: manual code entry, and the browser BarcodeDetector if present).
   GET /api/foods/barcode/{code} backed by Open Food Facts through a provider interface (fake in tests), cached in Mongo,
   per-100 g and per-serving mapping, attribution shown in the app, not-found falls back to custom food or photo.
4. **Water and reminders.** Quick-add water buttons (+150 / +250 / +500 ml, custom), a glass tracker, a daily goal
   derived from weight and activity (adjustable), undo via the toast. Reminder settings (meal times, water interval,
   quiet hours, per-type on/off) stored per user; schedule local notifications with expo-notifications behind a capability
   check so web and Expo Go show "available in the installed app" instead of failing. Real scheduling is verified in
   Phase 5; say that in PROGRESS.md.
5. **Challenges and badges.** Server-side challenge definitions (7-day protein target, 8k steps when available, log
   every meal for 5 days, water streak, no sugary drinks for a week, try a new vegetable) with progress computed from
   logs, opt-in joining, kind encouraging wording (no shaming, no loss-aversion tricks), badges shown in Insights and on
   the share card. Tests for progress rules and timezone edges.
6. **Regional cuisine and special-day modes (opt-in only).** Settings: cuisine focus (Andhra and Telangana, Tamil, Kerala,
   Karnataka, North Indian, Bengali, Gujarati, Maharashtrian, others) and optional "fasting or special days" the user
   picks themselves (for example vrat days, Sankranti, Ugadi, Diwali menus). The plan and suggestions respect them. The
   app never infers religion or beliefs, stores only the options the user chose, treats them as sensitive in the privacy
   policy, and never uses them for anything except suggestions. Tests.
7. **Home workout library.** 30+ routines (bodyweight, yoga flows, walking intervals, mobility and stretching) with
   original illustrated steps, a timer, filters (time, level, equipment, goal), English and Telugu, a plain safety note
   (general fitness information, stop if you feel pain, check with a doctor if unsure), and logging into Movement with an
   estimated calorie burn from MET values and the user's weight (labelled as an estimate). Tests for the calorie maths.
8. **Progress photos (optional, do last).** Private by design: stored only on the device (native filesystem, IndexedDB on
   web), never uploaded, included in no backup or analytics, deleted by the account-deletion flow on that device, with a
   before / after viewer. If time or memory is short, skip and list as not done.

## Not in this run (needs the real build or a decision)
Health Connect (steps, sleep, weight), verified push or local notification delivery, native Google sign-in, Google Play
Billing and premium, family or group sharing. These belong to Phase 5 / 6 or later.

## Finish
Add an "Extras run" section to docs/PROGRESS.md (what changed, what is verified, what needs the installed app, Telugu
strings and nutrition or MET values needing human review, privacy or Data Safety changes). Merge and stop. After each PR
note files changed, tests added, and what to verify on the phone.
