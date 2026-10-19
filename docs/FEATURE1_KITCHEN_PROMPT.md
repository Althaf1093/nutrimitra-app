# Feature 1: "My Kitchen" - plans built from what the user actually has and eats

Read CLAUDE.md and docs/PROGRESS.md. Run this only after the UX run (docs/UX_PROMPT.md) is merged. You are fully
autonomous; ask me nothing unless a blocker only I can solve. NEVER read, print or commit backend/.env or
frontend/.env. Same loop as before: one branch and PR per item, tests for every item (pytest and Playwright), tsc,
ESLint, web build, review your own screenshots, squash-merge when green. Full pytest and full e2e once at the end,
one after the other, never together (low-memory PC).

## Product idea (this is what makes Wellstride different)
Most apps give a generic plan. Wellstride first asks what the person really cooks and eats at home, then builds the
plan only from those ingredients and dishes, and adapts it daily from what they log. Inspiration is the polished,
simple feel of apps like HealthifyMe, but do NOT copy any competitor's layout, images, wording or branding.

## Items, in this order
1. **Kitchen onboarding step.** Add a friendly step after the body/goal steps (skippable, editable later in
   Settings > My Kitchen): "What do you usually have at home?" Multi-select chip groups with search, Indian-first:
   - Vegetables (brinjal, ladies finger, tomato, onion, potato, cabbage, cauliflower, beans, carrot, drumstick,
     gongura, spinach and other leafy greens, gourds, capsicum, pumpkin, beetroot, raw banana and more, 60+)
   - Staples (rice, wheat, ragi, jowar, bajra, oats, millets), pulses and dals, protein sources (egg, chicken, fish,
     paneer, curd, soya, sprouts, tofu; only those matching the user's diet preference), fruits, oils/ghee, and
     "I cook at home: how many meals per day" plus cooking time and number of people.
   Store as a kitchen profile on the user (backend model + validation + indexes; included in account deletion and
   data export). Ship the ingredient catalogue as a JSON data file with English and Telugu names. Tests for the
   endpoints (GET/PUT /api/kitchen) and for diet-preference filtering (a vegetarian never sees chicken).
2. **Plan from the kitchen.** Change plan generation so meals use the user's kitchen items first, with a short
   "also buy" list for at most a few missing items, still respecting diet, allergies, health-condition notes,
   calorie and protein targets, budget and cooking time. Add a weekly "Shopping list" view built from the plan
   minus what the user already has. Keep the wellness (not medical) disclaimer. Validate AI output against the
   food catalogue and the kitchen list, and fall back to a deterministic kitchen-based plan when the AI is busy.
   Tests with the fake AI: plan only uses allowed ingredients, honours diet, never exceeds the cap on extras.
3. **Daily loop.** On Today: show the day's planned meals from the kitchen plan, one-tap log (reuse the new toast
   and food search), "swap this meal" (3 alternatives from the same kitchen), "I ate something else", and an evening
   check-in that adapts tomorrow (for example, if protein was low, bias tomorrow's meals to protein-rich
   kitchen items). Keep it simple and honest: no medical claims. Tests for swap and adaptation.
4. **Settings > My Kitchen** to edit items anytime, with a prompt to regenerate the plan when the kitchen changes.
   English and Telugu strings for everything (list uncertain Telugu keys in docs/PROGRESS.md).

## Finish
Add a "Feature 1: My Kitchen" section to docs/PROGRESS.md (what changed, what is verified, what I must check on
the phone, items needing human review). Merge and stop. After each PR note: files changed, tests added, what to
verify on the phone.
