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

## Prioritized backlog

### P0 — next product-critical tasks
- Configure the managed Google OAuth handoff URL and complete the real Google sign-in callback.
- Add real camera/photo upload with base64 food image recognition, confirmation and substitutions.
- Persist coach conversation history and add meal/photo source metadata.

### P1 — high-value expansion
- Add reminders/notifications for meals, hydration, movement and weekly reviews.
- Add richer adaptive plan regeneration from logged meals, readiness and weekly review.
- Add native HealthKit and Android Health Connect permission/read adapters; distinguish device-reported metrics from estimates in every card.
- Add personalized home/gym/outdoor workout library, running guidance and sleep/readiness inputs.

### P2 — scale and differentiation
- Wearable connectors, family profiles, regional Indian languages and expert consultations.
- Searchable ingredient database expansion, barcode support and richer recipe substitutions.
- Accessibility audit with TalkBack/VoiceOver, offline queueing and deeper analytics controls.

## Next tasks list
1. Configure Google managed OAuth handoff and test the full callback.
2. Build photo recognition and confirmation as a permissioned base64 flow.
3. Add native health adapters and notification permissions.
4. Split the large mobile shell into maintainable route-level screens as feature depth grows.