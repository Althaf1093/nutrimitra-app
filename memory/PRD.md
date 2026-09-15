# NutriMitra Product Record

## Problem statement
NutriMitra is a premium, privacy-first AI wellness companion for India, initially in English and Telugu. It helps Indian IT professionals and homemakers understand their context, create an adaptive 7-day food and movement plan, track meals/activity/progress, get guidance throughout the day, and review the week safely without medical diagnosis or unrealistic promises.

## Architecture
- Mobile: Expo SDK 57 / React Native with a single mobile-first shell, safe-area insets, bilingual UI, secure token storage, and a calm journal/editorial visual system.
- Backend: FastAPI on port 8001 with JWT email/password auth, MongoDB collections for users, profiles, plans, meals, activities, weights, permissions, and future coach history.
- AI: server-side Groq adapter using `openai/gpt-oss-120b`, configured by environment variables and kept replaceable. Public coach verification returns live `source=groq`.
- Data safety: password hashes use bcrypt; JWTs are stored in SecureStore/native encrypted storage; MongoDB responses exclude `_id`; manual activity is labelled as an estimate.
- Future device layer: permission records and privacy UI are ready for HealthKit, Health Connect, wearables, and regional expansion without claiming device data that is not connected.

## User personas
- Indian IT professional balancing long workdays, affordable meals, movement and energy.
- Homemaker seeking practical family-friendly Indian nutrition and simple cooking guidance.
- Privacy-conscious wellness user who wants control over health permissions and language.

## Core requirements (static)
- Secure accounts, bilingual English/Telugu experience, onboarding profile, goals, allergies, dislikes, budget and cooking constraints.
- Adaptive 7-day Indian-focused meal plan with global nutritious ingredients, portions, estimated nutrition and simple reasoning.
- Daily dashboard, What Should I Eat Now, meal logging, manual activity, weight/progress, weekly perspective, AI coach, privacy controls and safety guidance.
- Architecture ready for photo recognition, substitutions, reminders, HealthKit/Health Connect, wearables, family features and expert consultations.

## Implemented (2026-09-14)
- Premium auth and onboarding flow with body metrics, preferences, goal, activity, cooking, budget, conditions, allergies, dislikes and language.
- MongoDB-backed JWT accounts and completed-profile session hydration on fresh login.
- 7-day plan generation with Indian/global ingredient rotation, nutrition macros, reasoning and a safe local nutrition engine fallback.
- Dashboard readiness score, meal cards, What Should I Eat Now modal and visible meal confirmation.
- Plan day navigation, meal logging, manual walking/home strength logging with estimate labels, weight logging and trend chart.
- Live Groq conversational coach with safety framing and Telugu response mode.
- Privacy/settings bottom sheet with health sync, wearable, analytics permission toggles, language selection and sign out.
- Stable preview/test selectors, runtime linting, backend regression coverage and public mobile verification at 390x844.

## Implemented (2026-09-15)
- Enterprise architecture refactor: monolithic index.tsx split into expo-router routes — welcome (auth), onboarding wizard, (tabs) Today/Plan/Coach/Progress (4 tabs, iOS 26 NativeTabs gated), modal screens eat-now, log-food, settings; shared AuthContext gate, i18n module, design-token style sheet, UI component library.
- Managed Google OAuth: `POST /api/auth/session` handoff exchange, `user_sessions` collection with 7-day tokens, dual JWT/session-token authentication, full native + web redirect handling.
- Food-photo recognition: `POST /api/coach/vision` with dynamic Groq vision-model selection from `/openai/v1/models` and Emergent universal-key fallback (Groq key currently lists zero vision models); confirm/edit UI with alternatives and meal-type chips; permissioned camera/gallery flow with Open Settings recovery.
- What Should I Eat Now: `GET /api/eat-now` computes Mifflin-based target, consumed and remaining calories and suggests the next unlogged plan meal; full-screen modal with one-tap logging.
- On-device reminders: expo-notifications local scheduling (meals, hydration, movement, weekly review), bilingual copy, permission flow with blocked/denied handling, prefs persisted via `GET/PUT /api/reminders`.
- Health adapter layer: normalized HealthRecord contract, idempotent `POST /api/health/sync`, app.json iOS/Android health permissions, native adapter templates for the installed build (`src/lib/health/native-adapters.md`).
- Keyboard upgrade to react-native-keyboard-controller; coach markdown flattening; contrast fix on dark hero cards.
- Tested: iteration 6 — 15/15 backend pytest, all web frontend flows passed.

## Implemented (2026-09-15, quality + coach pass)
- UI/UX quality pass: design-token style sheet rewritten with responsive constraints — `minWidth: 0` on flex text containers, explicit `lineHeight` on every heading/label (Telugu glyph clipping fix), `maxWidth: 100%` chips, `flexShrink: 0` on fixed row children, flexed hero-card text columns; audited at 390x844 and 320x568 in English and Telugu (iteration 7: no overflow, clipping, collapse or one-char-per-line wrapping found).
- Route guards: unauthenticated deep links to tabs/settings/eat-now/log-food redirect to welcome; loading states everywhere.
- AI Coach conversation memory (opt-out "Coach memory" privacy toggle, default on): history persisted to `coach_messages`, last 12 messages used as context, `GET /api/coach/history`, frontend restores on focus.
- Structured recipe cards in coach: fenced ```recipe JSON parsed/validated server-side, rendered as styled card with ingredients, steps and one-tap "Log as meal"; recipes persist through history restore.
- Privacy-first health sync: `POST /api/health/sync` returns 403 until the user enables Health sync in Settings.
- Tested: iteration 7 — 23/23 backend pytest, all frontend flows + layout audit passed in both languages and both viewport sizes.

## Prioritized backlog

### P0 — next product-critical tasks
- Complete a real Google OAuth sign-in on a device (handoff verified end-to-end in code; needs a human Google account).
- Persist coach conversation history and add meal/photo source metadata views.

### P1 — high-value expansion
- Install native health adapters (`@kingstinct/react-native-healthkit`, `react-native-health-connect`) at native-build time using the templates in `src/lib/health/native-adapters.md`; distinguish device-reported metrics from estimates in every card.
- Bundle Noto Sans Telugu via expo-font to remove web-preview Telugu shaping artifacts.
- Richer adaptive plan regeneration from logged meals, readiness and weekly review.
- Personalized home/gym/outdoor workout library, running guidance and sleep/readiness inputs.

### P2 — scale and differentiation
- Wearable connectors, family profiles, regional Indian languages and expert consultations.
- Searchable ingredient database expansion, barcode support and richer recipe substitutions.
- Accessibility audit with TalkBack/VoiceOver, offline queueing and deeper analytics controls.

## Next tasks list
1. Human-test Google sign-in on Expo Go (scan QR) and confirm the session lands on onboarding/Today.
2. Wire native health adapters into the dev build and surface steps/sleep on the Today screen.
3. Bundle a Telugu font (Noto Sans Telugu via expo-font) for the web preview to remove shaping artifacts.
4. Adaptive plan regeneration driven by logged meals and weekly review.