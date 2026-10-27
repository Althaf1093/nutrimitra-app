"""Builds data/nutrients.json from USDA FoodData Central, SR Legacy (public domain, CC0).

Download once (not committed):  https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
Run:  python -I tools/build_nutrients.py <folder with food.csv, nutrient.csv, food_nutrient.csv>

Each base food below is one USDA entry (by FDC id). Amounts are stored per 100 kcal of that food, so a dish is estimated
from calories and the share of its energy that comes from each base food (see nutrients.py). Where USDA has a "with salt"
cooked entry it is used, so sodium is not wildly low for cooked Indian food. Jaggery is approximated by molasses.
A nutrient USDA does not report for an entry is stored as 0 and listed under "missing" for that entry.
"""
import csv
import json
import sys
from pathlib import Path

NUTRIENT_IDS = {
    "iron": "1089", "calcium": "1087", "zinc": "1095", "magnesium": "1090", "potassium": "1092", "sodium": "1093",
    "vitamin_a": "1106", "vitamin_b12": "1178", "folate": "1190", "vitamin_c": "1162", "vitamin_d": "1114",
    "vitamin_e": "1109", "vitamin_k": "1185",
}
ENERGY_ID = "1008"

BASES = {
    "rice_white": 169753, "rice_brown": 169704, "wheat_flour": 168893, "bread_whole": 172688, "bread_white": 174924,
    "millet": 168871, "oats": 173905, "sorghum": 169716,
    "lentil": 175254, "chickpea": 173799, "kidney_bean": 175242, "mung": 175255, "pigeon_pea": 172472, "cowpea": 175252, "tofu": 172475,
    "spinach": 170531, "potato": 170114, "onion": 170100, "tomato": 170137, "cauliflower": 168520, "okra": 170098, "eggplant": 169352,
    "carrot": 169339, "cabbage": 169976, "green_peas": 170102, "green_beans": 169321, "mushroom": 168537, "capsicum": 170515,
    "mustard_greens": 170503, "drumstick": 168532, "broccoli": 168510, "corn": 168525, "sweet_potato": 170541, "pumpkin": 168448,
    "cucumber": 168409, "radish": 169276, "gourd": 169232, "bitter_gourd": 168393, "beet_greens": 168508,
    "banana": 173944, "apple": 171688, "mango": 169910, "orange": 169097, "papaya": 169926, "guava": 173044, "grapes": 174683,
    "watermelon": 167765, "pineapple": 169124, "pomegranate": 169134, "coconut": 170169, "dates": 168191,
    "milk": 171265, "yogurt": 171284, "paneer": 172179, "egg": 173424, "chicken": 171054, "fish": 175177, "shrimp": 171971, "lamb": 172616,
    "oil": 172370, "ghee": 171314, "butter": 173410, "sugar": 169655, "honey": 169640, "jaggery": 168820, "dark_chocolate": 170272,
    "almond": 170567, "peanut": 172430, "cashew": 170162, "sesame": 170150, "flaxseed": 169414, "walnut": 170187, "pistachio": 170184,
}


def main(folder: Path, out: Path) -> None:
    foods = {int(row["fdc_id"]): row["description"] for row in csv.DictReader(open(folder / "food.csv", encoding="utf-8"))}
    wanted = {str(fdc) for fdc in BASES.values()}
    amounts = {}
    for row in csv.DictReader(open(folder / "food_nutrient.csv", encoding="utf-8")):
        if row["fdc_id"] in wanted:
            amounts[(row["fdc_id"], row["nutrient_id"])] = float(row["amount"])
    bases = {}
    for key, fdc in BASES.items():
        kcal = amounts.get((str(fdc), ENERGY_ID))
        if not kcal:
            raise SystemExit(f"{key}: FDC {fdc} has no energy")
        per_100kcal, missing = {}, []
        for nutrient, nid in NUTRIENT_IDS.items():
            value = amounts.get((str(fdc), nid))
            if value is None:
                missing.append(nutrient)
                value = 0.0
            per_100kcal[nutrient] = round(value / kcal * 100, 3)
        bases[key] = {"fdc_id": fdc, "description": foods[fdc], "kcal_per_100g": kcal, "per_100kcal": per_100kcal, "missing": missing}
    doc = {
        "version": 1,
        "source": "USDA FoodData Central, SR Legacy (April 2018). Public domain (CC0). https://fdc.nal.usda.gov/",
        "note": "Amounts per 100 kcal of each base food. Estimates only; see nutrients.py for how dishes are put together.",
        "nutrient_ids": NUTRIENT_IDS,
        "bases": bases,
    }
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(bases)} base foods written to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(__file__).resolve().parent.parent / "data" / "nutrients.json")
