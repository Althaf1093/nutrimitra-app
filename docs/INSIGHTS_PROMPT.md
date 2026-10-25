# Insights run: KPIs, habit score, best and worst day, patterns, shareable weekly card

Read CLAUDE.md, docs/PROGRESS.md and docs/design-mock/ (Progress.dc.html and ShareCard.dc.html are the visual targets).
Run after the Logging run and the Design run are merged. You are fully autonomous; ask me nothing unless a blocker only I
can solve. NEVER read, print or commit backend/.env or frontend/.env. One branch and PR per item, tests for each item
(pytest and Playwright), tsc, ESLint, web build, review your own screenshots at phone and desktop sizes in English and
Telugu, squash-merge when green. Full pytest and full e2e once at the end, one after the other, never together.

## Principles
- Honest numbers only. Every KPI comes from data the user logged or a device reports. No fabricated scores, no health
  claims, no "medical" language. Show the formula behind the habit score ("How is this calculated?" sheet).
- If data is missing (for example no steps without Health Connect), hide that tile or show "Connect to see this", never 0.
- Everything is explainable in plain English and Telugu.

## Items, in this order
1. **Analytics endpoint.** GET /api/insights?range=week|month|quarter (user timezone aware). Returns per day: calories,
   protein, carbs, fat, fibre, water, active minutes, steps if available, meals logged, dinner time; plus aggregates and
   deltas vs the previous period. Efficient Mongo aggregation with the existing indexes; tests with seeded users,
   including timezone edges and empty ranges.
2. **Habit score (0-100), transparent.** Components and weights, each 0-100 then weighted: Calories on target 20
   (within +-10% of target = full, linear down to 0 at +-40%), Protein 20 (eaten / target, capped at 100%), Fibre 15,
   Water 15, Movement 15 (active minutes vs goal), Consistency 15 (days with at least 2 meals logged). Missing
   components are excluded and the others re-weighted; say so in the UI. Return the per-component values and the
   week-over-week change. Unit tests for the formula and edge cases.
3. **KPI grid and heatmap.** Tiles: avg calories vs target, protein target hit days (x / 7) and average, avg fibre,
   avg water, avg steps, active minutes per day, logging streak and best streak, weight change. Heatmap rows (calories,
   protein, fibre, water, steps) by day with green / amber / red thresholds defined in one config; today's partial day
   is shown neutral. Accessible: colour is never the only signal (show the value and a text label).
4. **Best day and needs-attention day** with the reason (which components were highest or lowest and their values).
5. **Pattern insights (rule-based, deterministic).** Implement as a small rules engine returning typed insights with
   numbers, then render localized English and Telugu sentences from templates (no free-form AI text for numbers).
   Rules to start with: weakest weekday vs weekday average (calories up, protein down, steps down), low-protein meal
   slot (for example dinner), late dinners (after 10 pm, count), water drops on low-step days, weekend effect, repeated
   items (for example sweet tea cups), protein or fibre consistently under target, streak risk. Each insight needs a
   minimum data threshold (for example 5 logged days) and a suggested action ("Add curd or paneer at dinner").
6. **Eat more / cut back lists** from logged foods against the user's goal and kitchen (rules, not medical advice).
7. **Nutrient check (estimates).** Only if the food catalogue has micronutrient fields for enough foods; otherwise ship
   it behind a flag, off by default, and list it as not done. Label as estimates; no supplement advice.
8. **Shareable weekly card.** Render the ShareCard design (9:16) from real numbers in the user's language and share it
   through the system share sheet (WhatsApp and Instagram stories): react-native-view-shot + expo-sharing on native, a
   download on web. Contains no personal identifiers beyond what the user sees; first-share consent text. Test the render.
9. **Telugu and English** strings for every label, insight template and card; list Telugu strings you are unsure of
   in docs/PROGRESS.md for a native reader.

## Finish
Add an "Insights run" section to docs/PROGRESS.md (what changed, what is verified, what I must check on the phone, what
needs Health Connect or micronutrient data, formulas used). Merge and stop. After each PR note files changed, tests added,
and what to verify.
