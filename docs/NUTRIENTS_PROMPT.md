# Fibre and micronutrients (vitamins and minerals)

Owner request (Althaf, 2026-10-26): fibre never counts on Today, and he wants vitamins and minerals analysed too (iron, B12, A, D, E, K and the rest).
Do this right after the current Design item, as TWO PRs, one after the other. Tick the lines in docs/PROGRESS.md "Pending fixes".

## PR 1: Fibre (small, do first)
Cause: the catalogue (backend/data/foods.json and backend/data/foods/*.txt) has no fibre, and the meal add/edit form has no fibre field.
1. Add a fibre_g column to every catalogue row (all 2,688 foods), estimated per serving, estimate: true. High for vegetables, dal, legumes, millets,
   oats, fruit with skin, nuts, seeds, brown rice, whole wheat roti; near zero for eggs, meat, fish, milk, oil, sugar, refined rice, drinks.
   Update load_compact, the README line in backend/data/foods/README.txt and docs/FOOD_DATA_SOURCES.md. Calories stay 4p + 4c + 9f + 7alc (fibre is informational).
2. Pass fibre_g through every logging path: food sheet, plan meals, kitchen meals, photo logging, custom food, "I ate something else".
3. Optional "Fibre (g)" field in the meal edit form and the custom food form.
4. Today Fibre bar: purple with a target once any logged meal has fibre; otherwise say "Add fibre to track", not "-/0 g".
5. Tests: every catalogue row has fibre_g (data test), dashboard fibre_g sums logged meals, UI test for the new field.

## PR 2: Vitamins and minerals
Nutrients to track (per food, per serving, estimates): iron, calcium, zinc, magnesium, potassium, sodium, vitamin A (RAE), vitamin B12, folate,
vitamin C, vitamin D, vitamin E, vitamin K. Keep the list in one config so it is easy to extend.
Data sources (licences matter, write them in docs/FOOD_DATA_SOURCES.md):
- Use USDA FoodData Central (public domain, CC0) for base ingredients (download the CSV or use the API with a key the owner provides; never commit keys).
- Map our 656 ingredients to USDA entries, then compute dishes from their ingredients (recipe-based) where we have recipes, and category defaults otherwise.
- Do NOT copy the Indian Food Composition Tables (IFCT 2017) wholesale (licence unclear). The owner may later supply permitted values.
- Every value is estimate: true. Dishes without a good estimate get null, never 0. Null means "not tracked", and the UI says so.
Reference daily amounts: use ICMR-NIN 2020 Recommended Dietary Allowances for Indian adults (by sex, with a pregnancy/lactation row left out, app is 18+ general wellness).
Store the table in backend/data/rda.json with source and year. Blank where unsure; do not invent.
Backend: save micronutrients on each meal like fibre; /api/dashboard returns a nutrients object (totals so far today, reference amount, percent, tracked flag);
add a weekly average endpoint or extend the Insights data (docs/INSIGHTS_PROMPT.md) with a 7-day average per nutrient.
Frontend (match the design tokens and docs/design-mock look):
- Today: a compact "Vitamins and minerals" card under the macros, a row of small bars (percent of daily reference), the 3 lowest highlighted, tap to expand all.
- Insights tab: 7-day average per nutrient, "often low" list, and food suggestions from what is in My Kitchen (rule-based, EN and TE templates, no AI claims).
- Telugu names for every nutrient, EN and TE copy reviewed later by a native reader.
Wording rules (important): general wellness information, never medical advice. No deficiency diagnosis, no supplement dosing, no treating words.
Say "your logged food is low in iron so far" not "you are iron deficient". Show a note: values are estimates and depend on how food is cooked.
Tests: data test (every ingredient has the nutrient fields or null), RDA file test, dashboard totals test, UI test for the card, EN and TE strings present.
After merging: post the summary, including how many foods have real estimates and how many are null, so the owner knows how complete it is.
