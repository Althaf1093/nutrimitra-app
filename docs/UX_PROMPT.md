# UX run: professional feedback toasts and smart food search

Read CLAUDE.md and docs/PROGRESS.md. You are fully autonomous: do items 1-3 end to end without asking me anything
unless you hit a blocker only I can solve. NEVER read, print or commit backend/.env or frontend/.env.
Same loop as before for each item: branch from up-to-date main, implement, add tests (backend pytest and/or an
e2e Playwright flow), run tsc, ESLint, the relevant tests and the web build, look at real screenshots of the result
yourself, open the PR, squash-merge when green, pull main. Full pytest suite and full e2e run once at the end only,
one after the other, never together (this PC runs low on memory).

## Why
The owner tested the web app and dislikes two things. Reference feel: HealthifyMe (polished, fast logging).
1. The "Meal logged" / "Removed" message is a full-width black bar that sits on the screen until tapped. It looks
   unprofessional and in the way (screens: Today meals list and Movement section).
2. Logging food by typing is too bare. Typing "egg" should suggest "Boiled egg", "Omelette", "Scrambled egg",
   "Fried egg (half-fry)", "Egg curry"; "idli" should suggest idli variants; "dosa" should suggest Plain dosa,
   Masala dosa, Ragi dosa, Karam dosa, Rava dosa, Pesarattu, Set dosa, Onion dosa, and so on. Many suggestions.

## Items, in this order

1. **Toast system.** Build one reusable toast (frontend/src/components/toast.tsx plus a provider/hook, e.g.
   useToast().show(message, {type})) and replace every ad-hoc message bar in the app (Today, Plan, Progress, Coach,
   Settings, Log food, anything using `styles.toast`). Requirements:
   - Small rounded pill/card, not full width: max width about 420 and centred, a small icon (check for success,
     info, warning for errors), soft shadow, theme colours (cream and green, a subtle dark surface or a light card
     with a green accent; not a heavy black slab), readable in English and Telugu.
   - Appears above the tab bar, slides/fades in, **auto-dismisses after about 2.5 seconds** (4 seconds for errors),
     never blocks taps on the screen behind it, can be swiped or tapped away, and never stacks: a new toast
     replaces the old one.
   - Optional "Undo" action for logging a meal and for removing an item, which reverses the action.
   - Accessible (announced to screen readers, role alert/status) and keeps the existing testIDs working or updates
     the e2e flows that used them.
   - Tapping "+" to log a plan meal adds it immediately with no extra step, shows the toast briefly, and the "+"
     button turns into the logged check right away (optimistic update, roll back with an error toast if the API fails).

2. **Food database and search suggestions.**
   - Backend: add a curated food catalogue (a JSON data file, not hard-coded in server.py) of at least 400 common
     foods, Indian-first (south Indian tiffins, north Indian, rice and dal, curries, snacks, sweets, drinks, fruits,
     eggs, chicken, fish, paneer, millets) plus common global foods. Each item: id, name, optional Telugu name,
     category, base term(s)/synonyms, default serving (for example "1 piece", "1 bowl (150 g)"), calories, protein,
     carbs, fat per serving, and additional serving options where sensible. Group variants under a base so that
     typing "egg" or "dosa" surfaces the whole family: eggs (boiled, half-boiled, omelette, scrambled, fried,
     egg curry, egg bhurji, egg white), idli (plain, ragi, rava, mini, podi idli), dosa (plain, masala, ragi, karam,
     rava, set, pesarattu, onion, ghee roast, oats, millet), upma, poha, paratha varieties, rice varieties, dal
     varieties, and so on. Use sensible, clearly-approximate nutrition values and mark them as estimates; do not
     invent precise-looking numbers.
   - Endpoint GET /api/foods/search?q=...&limit=... (auth required): case-insensitive prefix and substring match on
     name, synonyms and Telugu names, light typo tolerance, ranked (exact and prefix first, then popular items, then
     the user's recently logged foods first), returns the variant list. Also GET /api/foods/recent for the user's
     last distinct logged foods. Rate limit sensibly and index nothing in Mongo that needs a heavy import; loading
     from the JSON at startup is fine.
   - Tests: egg -> includes boiled egg and omelette; dosa -> at least 8 dosa variants including ragi and karam;
     idli; typos like "dosaa"; Telugu query; ranking of recents; auth required; empty query returns recents.

3. **Log-food screen redesign** (frontend/app/log-food.tsx and any helper components).
   - One search box at the top, focused, with the suggestion list appearing under it as you type (debounced about
     200 ms): each row shows the name, serving and kcal, and a one-tap "+" add. Tapping a row opens a compact
     bottom sheet to pick the serving size (stepper for quantity, serving chips) and meal slot (breakfast / lunch /
     snack / dinner, defaulting by time of day), with live kcal and protein, then "Add". One-tap "+" on a row adds
     the default serving to the default slot immediately.
   - Sections when the box is empty: Recent, Frequent, and a few quick category chips (Eggs, Dosa, Idli, Rice, Dal,
     Curry, Snacks, Fruits, Drinks).
   - Keep the existing manual-entry and Photo paths available (for example "Can't find it? Add custom food" and the
     camera button) and keep them working.
   - If the search request fails, show the new toast and keep typed text; show a clear empty state ("No match, add
     it yourself") when nothing matches.
   - All new text in src/i18n.ts in English and Telugu (list Telugu keys you are unsure of in docs/PROGRESS.md).
   - Add or update Playwright flows: type "egg", see Boiled egg, add it, see the brief toast disappear on its own and
     the meal on Today; type "dosa" and see at least 8 variants; check there is no full-width black bar and that
     the toast is gone after about 3 seconds. Take screenshots and review them yourself.

## Finish
Add a "UX run" section to docs/PROGRESS.md: what changed, what is verified, what I must check on the phone, and the
list of Telugu strings and food values needing human review (nutrition values are estimates; a nutritionist should
review before launch). Merge it and stop. After each PR, note: files changed, tests added, and what to verify.
