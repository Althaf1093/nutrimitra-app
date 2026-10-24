# Logging run: user-driven food logging, a much bigger food list (drinks included), and photo snap

Read CLAUDE.md and docs/PROGRESS.md. You are fully autonomous; ask me nothing unless a blocker only I can solve.
NEVER read, print or commit backend/.env or frontend/.env. Same loop as before: one branch and PR per item, tests for
every item (pytest and Playwright), tsc, ESLint, web build, review your own screenshots, squash-merge when green.
Full pytest and full e2e once at the end, one after the other, never together (low-memory PC).

## What the owner said (screenshot of the Today screen)
The Today screen is pre-filled with plan meals (Brown rice dal plate, Greek yogurt fruit bowl...) and a "+" that logs
them as eaten. He does not want defaults appearing like that. The user should choose what they ate: type and pick
from a big list, or snap a photo. Plan meals are only suggestions. The food list must cover almost everything people
eat and drink, including tea (green, ginger, masala, milk tea), coffee, juices, lassi, buttermilk, and also beer,
whisky, rum, wine and other alcohol. Kitchen setup should also be pick-from-a-big-list, with a snap option.

## Items, in this order

1. **Today = what I actually ate.** Rework the Today meals area so it shows only what the user has logged, grouped
   by Breakfast, Lunch, Snack, Dinner (plus an optional "Drinks" group or slot). Every slot has a clear "+ Add food"
   button that opens one add sheet with: a search box (the existing food search), a prominent camera button
   ("Snap your meal"), Recent and Frequent items, and "Add custom food". Plan meals are NOT shown as pre-filled
   items with a log button any more. Show them as a small collapsed "Suggestion for lunch" link per slot; opening it
   shows the plan meal with Swap and an explicit "Log this" button. Keep "I ate something else" behaviour working
   through the new add sheet. Calories and macros on top reflect only what was logged. Empty days look friendly
   ("Nothing logged yet - add your first meal"). Update the daily loop, evening check-in, e2e flows and tests that
   assumed pre-filled meals. English and Telugu strings.

2. **Photo snap, one tap.** From the add sheet the camera opens straight away (web: file picker with capture on
   mobile browsers); after the photo is taken, run the existing vision flow, show the detected dishes with portion
   editing in the existing confirm form, let the user fix names by searching the catalogue, then log. Handle the
   AI-busy case with the toast and a "search instead" path. Never store the image unless the owner's privacy
   policy already says so; keep current behaviour and say what it is in PROGRESS.md.

3. **Big food and drink catalogue (target 2,500+ items).** Extend backend/data/foods.json (or split into several
   data files loaded at startup) with: all common Indian dishes by region (Andhra and Telangana, Tamil, Kerala,
   Karnataka, North Indian, Gujarati, Bengali, Maharashtrian, street food), restaurant dishes, biryanis,
   curries by main ingredient, breads, rice dishes, sweets and desserts, snacks and namkeen, fruits, vegetables,
   nuts, dairy, meats, seafood, eggs, packaged and fast food staples, global dishes, and DRINKS: water, tea
   (plain milk chai, ginger/adrak, masala, green, black, lemon, iced tea), coffee (filter, black, cappuccino, latte,
   cold coffee), juices, coconut water, lassi, buttermilk, sugarcane juice, soft drinks, energy drinks, protein
   shakes, and alcohol (beer regular/strong/light in 330 ml and 650 ml, whisky/rum/vodka/gin per 30 ml and 60 ml
   peg, wine per glass, common cocktails). For drinks use ml servings. Alcohol rows are for honest calorie tracking
   only: neutral wording, no encouragement, no health claims, and keep the app's 18+ rule.
   Data quality: prefer public-domain or openly licensed sources for generic foods (USDA FoodData Central is
   public domain; check the licence of anything else, including Indian Food Composition Tables, before copying
   values, and record every source and licence in docs/FOOD_DATA_SOURCES.md). Where a source is not reachable, write
   plausible estimates and mark those rows `estimate: true`. Include Telugu names where you are confident.
   Add a data validation test (required fields, sane calorie ranges, macros consistent with calories within a
   tolerance, no duplicate ids, search finds "masala tea", "green tea", "beer", "whisky", "ragi dosa", "biryani").
   Optional second source: if a food is not found, offer "Search packaged foods" backed by Open Food Facts (free,
   ODbL, attribution required) behind a provider interface with a fake in tests; include the attribution in the
   app and PROGRESS.md. Skip this sub-item if it risks the run; list it as not done.

4. **Kitchen setup from a big list, plus snap.** Expand the My Kitchen ingredient catalogue to cover essentially
   every common ingredient (vegetables, leafy greens, pulses, grains, millets, spices, masalas, oils, dairy, meats,
   seafood, fruits, dry fruits, condiments, packaged staples) with search and category tabs, English and Telugu.
   Add a "Snap your kitchen" option: the user photographs the fridge, shelf or groceries; the vision provider lists
   the ingredients it sees; the user confirms or edits the list before it is saved (never save without confirmation).
   Tests with the fake vision provider.

## Finish
Add a "Logging run" section to docs/PROGRESS.md (what changed, what is verified, what I must check on the phone,
food-data sources and review needs: a nutritionist should review nutrition values and alcohol servings; Telugu
strings needing a native reader). Merge and stop. After each PR note: files changed, tests added, what to verify.
