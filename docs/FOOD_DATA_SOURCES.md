# Food data sources and licences

Files: `backend/data/foods.json` (the original 589 foods) and `backend/data/foods/*.txt` (about 2,100 more rows, loaded
at startup by `backend/foods.py`, format described in `backend/data/foods/README.txt`).

## Where the numbers come from
- **No external dataset was copied.** USDA FoodData Central (public domain) and the Indian Food Composition Tables
  (licence not checked) were not used in this run. Every value is an estimate written from general nutrition knowledge
  for a typical home or restaurant serving, then rounded.
- Every row loaded from `data/foods/*.txt` is marked `estimate: true`, and the app labels all food values as estimates.
- Calories in those rows are calculated from the macros (4 kcal/g protein and carbs, 9 kcal/g fat, 7 kcal/g alcohol), so
  calories and macros always agree. Fibre is not subtracted, so some high-fibre foods read a little high. Every row also has an estimated fibre_g (tools/add_fibre.py: a share of the carbohydrate by food type, in half-gram steps, capped at 14 g per serving); it is informational and not part of the calories.
- `generated_combos.txt` is produced from a main ingredient plus a cooking style (for example "Okra fry", "Chicken korma")
  using a base value for the ingredient and a fixed oil/sauce add-on per style. These are the roughest rows. Treat them as
  ballpark figures until a nutritionist reviews them.
- Alcohol rows (category "Alcohol") are for honest calorie tracking only. Servings are bottles, pints, 30 ml and 60 ml
  pegs and glasses. The app keeps its 18+ rule and the wording stays neutral.

## Review needed before launch
- A nutritionist should review the values, in particular alcohol servings, restaurant portions and the generated rows.
- A native Telugu reader should review the Telugu names. Most are transliterations or common names; compound names such
  as "చికెన్ కూర" are built from a dish word plus a style word.

## Not done
- Open Food Facts lookup for packaged foods (ODbL, attribution required) is not built. If added later it must sit behind
  a provider interface with a fake in tests, and the app and this file must carry the attribution.
- Replacing estimates with USDA or IFCT values. If done, record each source and licence here.
