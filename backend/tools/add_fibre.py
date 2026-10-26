"""One-off: adds an estimated fibre_g to every catalogue row (data/foods.json and data/foods/*.txt).

Fibre is estimated per serving as a share of the row's carbohydrate, by food type (see RULES), never more than the carbs.
Foods with no carbohydrate to speak of (meat, fish, eggs, oil, plain dairy, most drinks) get 0. Every value is an estimate.
Run once:  python tools/add_fibre.py   (it refuses to run on rows that already have fibre).
New rows should carry their own fibre_g; this script is kept so the rule is written down and can be re-checked.
"""
import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# (share of carbohydrate that is fibre, words that put a food in the group). First match wins, so list specific groups first.
RULES = [
    (0.45, ["almond", "walnut", "cashew", "pistachio", "peanut", "groundnut", "flax", "chia", "sesame", "pumpkin seed", "sunflower seed", "seeds", "nuts", "dry fruit", "trail mix"]),
    (0.30, ["rajma", "chana", "chole", "chickpea", "lentil", "moong", "dal", "daal", "sambar", "bean", "peas", "sprout", "soya", "usal", "horse gram", "kulthi"]),
    (0.22, ["salad", "sabzi", "bhaji", "palak", "spinach", "methi", "saag", "cabbage", "cauliflower", "gobi", "okra", "bhindi", "beans", "brinjal", "baingan",
            "drumstick", "gourd", "lauki", "bitter", "karela", "carrot", "beetroot", "broccoli", "mushroom", "capsicum", "vegetable", "veg ", "mixed veg", "curry leaf",
            "cucumber", "tomato", "onion", "pumpkin", "radish", "turnip", "raw banana", "plantain", "avial", "poriyal", "kootu", "thoran", "stir fry"]),
    (0.18, ["apple", "guava", "pear", "orange", "papaya", "pomegranate", "berry", "berries", "kiwi", "avocado", "fig", "anjeer", "dates", "date ", "coconut", "jamun", "amla"]),
    (0.12, ["ragi", "jowar", "bajra", "millet", "oats", "oatmeal", "porridge", "whole wheat", "wholewheat", "atta", "brown rice", "multigrain", "quinoa", "barley",
            "roti", "chapati", "phulka", "paratha", "thepla", "bhakri", "dalia", "daliya", "muesli", "granola", "whole grain", "wholegrain", "poha", "upma", "dosa", "idli"]),
    (0.10, ["banana", "mango", "grape", "pineapple", "watermelon", "melon", "fruit", "chikoo", "sapota", "lychee", "jackfruit", "custard apple"]),
    (0.03, ["white rice", "rice", "biryani", "pulao", "naan", "kulcha", "maida", "bread", "pizza", "burger", "pasta", "noodles", "puri", "bhatura", "sandwich", "fries", "samosa", "kachori",
            "cake", "biscuit", "cookie", "chips", "namkeen", "halwa", "laddu", "ladoo", "barfi", "burfi", "jalebi", "gulab", "rasgulla", "payasam", "kheer", "sweet"]),
]
DEFAULT_SHARE = 0.06
# Drinks made of liquids, sugar or animal food have no fibre unless a plant food is named in them.
NO_FIBRE = ["juice", "soda", "cola", "soft drink", "energy drink", "beer", "wine", "whisky", "whiskey", "rum", "vodka", "gin", "brandy",
           "cocktail", "sugar", "honey", "jaggery water", "syrup", "ice cream", "kulfi", "milkshake", "lassi", "buttermilk", "chaas", "tea", "coffee",
           "milk", "curd", "yogurt", "yoghurt", "raita", "paneer", "cheese", "ghee", "butter", "oil", "egg", "omelette", "chicken", "mutton", "lamb",
           "fish", "prawn", "shrimp", "crab", "pork", "beef", "keema", "kebab", "tikka", "sausage", "tuna", "salmon", "sardine"]
PLAIN_CATEGORIES = ("eggs", "chicken", "mutton", "fish & seafood", "alcohol")


def matches(words, text: str) -> bool:
    return any(re.search(r"(?<![a-z])" + re.escape(word.strip()) + r"(?:s|es)?(?![a-z])", text) for word in words)


def fibre_for(name: str, category: str, carbs: float) -> float:
    if carbs < 1:
        return 0.0
    text = f" {name} ".lower()
    kind = category.lower()
    if kind == "alcohol":
        return 0.0
    if kind in PLAIN_CATEGORIES:
        share = 0.03 if carbs >= 15 else 0.0  # a rice or bread side with the meat, fish or egg
    else:
        share = 0.0 if kind in ("drinks", "dairy & paneer") else (0.03 if kind == "sweets" else DEFAULT_SHARE)
        if kind == "drinks" and matches(NO_FIBRE, text):
            share = 0.0
        else:
            for rule_share, words in RULES:
                if matches(words, text):
                    share = rule_share
                    break
    return round(min(carbs, carbs * share, 14) * 2) / 2  # half-gram steps: false precision would mislead


def main() -> None:
    foods_path = DATA / "foods.json"
    doc = json.loads(foods_path.read_text(encoding="utf-8"))
    if any("fibre_g" in row for row in doc["foods"]):
        sys.exit("foods.json already has fibre_g")
    for row in doc["foods"]:
        row["fibre_g"] = fibre_for(row["name"], row["category"], float(row["carbs_g"]))
    foods_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    count = 0
    for path in sorted((DATA / "foods").glob("*.txt")):
        if path.name.lower() == "readme.txt":
            continue
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                out.append(line)
                continue
            parts = [part.strip() for part in line.split("|")]
            parts += [""] * (9 - len(parts))
            name, te, category, serving, protein, carbs, fat, alcohol, synonyms = parts[:9]
            fibre = fibre_for(name, category, float(carbs or 0))
            out.append("|".join([name, te, category, serving, protein, carbs, fat, alcohol, f"{fibre:g}", synonyms]))
            count += 1
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"fibre added to {len(doc['foods'])} rows in foods.json and {count} rows in data/foods/*.txt")


if __name__ == "__main__":
    main()
