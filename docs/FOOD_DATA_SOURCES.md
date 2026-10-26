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

## Vitamins and minerals (nutrients PR 2)
- **Source:** USDA FoodData Central, SR Legacy (April 2018), public domain (CC0), https://fdc.nal.usda.gov/. 73 base foods (one USDA entry each, listed with their FDC ids in `backend/tools/build_nutrients.py`), stored per 100 kcal in `backend/data/nutrients.json`. The CSV download is not committed. Where USDA has a "with salt" cooked entry it is used, so sodium is not far too low for cooked food. Jaggery is approximated by molasses. A nutrient USDA does not report for an entry is stored as 0 and listed under `missing` for that entry.
- **How a dish is estimated:** `backend/nutrients.py`. A food name is matched to a profile (the share of its energy from each base food, e.g. dal = lentils + pigeon peas + oil + onion + tomato) by keywords, then by catalogue category. Nutrients = calories x profile. The amounts are not weighed recipes: they are rough, every one is an estimate, and cooking changes real values. Not used: IFCT 2017 (licence unclear).
- **Not tracked (no estimate, shown as "not tracked", never as 0):** alcohol, tea and coffee, soft and energy drinks, juices, packaged and processed foods (noodles, pizza, burgers, biscuits, chocolate, cereal ...), sauces, chutneys and pickles. A meal with a name we cannot place (a custom food) is also not tracked.
- **Coverage:** 2,252 of the 2,688 catalogue foods have an estimate (84%); 436 have none (169 drinks, 113 snacks, 68 alcohol, 22 sweets, 19 rice and mains, 13 salads, 8 tiffin, 7 nuts and seeds, the rest packaged).
- **Reference amounts:** `backend/data/rda.json`, ICMR-NIN 2020 adult values (sedentary, no pregnancy or lactation rows). Entered from memory of the printed table and marked `checked: false` for every nutrient: **the owner must check each against the ICMR-NIN 2020 table before launch.** Vitamin E, vitamin K, potassium, sodium and vitamin D are the least certain. For a person not recorded as Male or Female the lower of the two values is used. Sodium is a limit to stay under, not a target.
