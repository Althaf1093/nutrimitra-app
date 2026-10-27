"""Vitamins and minerals: estimates per food, daily reference amounts and the Today / Insights totals.

How a number is made (all of it an estimate, general wellness information, not medical advice):
- data/nutrients.json holds, for about 70 base foods, the amount of each nutrient per 100 kcal (USDA FoodData Central SR Legacy, CC0).
- A food or meal is described by a PROFILE: the share of its energy that comes from each base food (dal = lentils + oil + onion + tomato ...).
- nutrient in a serving = calories x sum(share x amount per 100 kcal) / 100.
- A name is matched to a profile by KEYWORD_PROFILES, then by the catalogue category. No match, or a packaged / drink / alcohol food, gives None:
  "not tracked", never 0.
- Reference amounts are in data/rda.json (ICMR-NIN 2020 Recommended Dietary Allowances for Indian adults; see the file for what still needs checking).
To add a nutrient: add it to NUTRIENTS, to tools/build_nutrients.py (USDA id), re-run that tool, and add it to rda.json.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA = Path(__file__).resolve().parent / "data"

# key, English name, Telugu name, unit, group. One list, so the rest of the app follows it.
NUTRIENTS: List[Dict[str, str]] = [
    {"key": "iron", "en": "Iron", "te": "ఇనుము", "unit": "mg", "group": "mineral"},
    {"key": "calcium", "en": "Calcium", "te": "కాల్షియం", "unit": "mg", "group": "mineral"},
    {"key": "zinc", "en": "Zinc", "te": "జింక్", "unit": "mg", "group": "mineral"},
    {"key": "magnesium", "en": "Magnesium", "te": "మెగ్నీషియం", "unit": "mg", "group": "mineral"},
    {"key": "potassium", "en": "Potassium", "te": "పొటాషియం", "unit": "mg", "group": "mineral"},
    {"key": "sodium", "en": "Sodium", "te": "సోడియం", "unit": "mg", "group": "mineral"},
    {"key": "vitamin_a", "en": "Vitamin A", "te": "విటమిన్ A", "unit": "µg", "group": "vitamin"},
    {"key": "vitamin_b12", "en": "Vitamin B12", "te": "విటమిన్ B12", "unit": "µg", "group": "vitamin"},
    {"key": "folate", "en": "Folate", "te": "ఫోలేట్", "unit": "µg", "group": "vitamin"},
    {"key": "vitamin_c", "en": "Vitamin C", "te": "విటమిన్ C", "unit": "mg", "group": "vitamin"},
    {"key": "vitamin_d", "en": "Vitamin D", "te": "విటమిన్ D", "unit": "µg", "group": "vitamin"},
    {"key": "vitamin_e", "en": "Vitamin E", "te": "విటమిన్ E", "unit": "mg", "group": "vitamin"},
    {"key": "vitamin_k", "en": "Vitamin K", "te": "విటమిన్ K", "unit": "µg", "group": "vitamin"},
]
KEYS = [item["key"] for item in NUTRIENTS]
# Sodium is a "keep it moderate" nutrient: it is shown, but never listed as "low".
LIMIT_NUTRIENTS = {"sodium"}

_BASES: Dict[str, Dict[str, Any]] = json.loads((DATA / "nutrients.json").read_text(encoding="utf-8"))["bases"]
RDA: Dict[str, Any] = json.loads((DATA / "rda.json").read_text(encoding="utf-8"))

# Profiles: share of a serving's energy by base food. Shares add up to 1. Vegetables carry little energy, so their shares are small
# (a palak dish with 150 g of spinach is under a fifth of its energy). tests/test_nutrients.py checks the weights this implies are plausible.
PROFILES: Dict[str, Dict[str, float]] = {
    "dal": {"lentil": 0.35, "pigeon_pea": 0.2, "oil": 0.25, "onion": 0.08, "tomato": 0.12},
    "dal_mung": {"mung": 0.55, "oil": 0.25, "onion": 0.08, "tomato": 0.12},
    "chana": {"chickpea": 0.6, "oil": 0.2, "onion": 0.08, "tomato": 0.12},
    "rajma": {"kidney_bean": 0.55, "oil": 0.2, "onion": 0.08, "tomato": 0.12, "rice_white": 0.05},
    "lobia": {"cowpea": 0.6, "oil": 0.2, "onion": 0.08, "tomato": 0.12},
    "sambar": {"pigeon_pea": 0.4, "oil": 0.2, "drumstick": 0.05, "tomato": 0.1, "onion": 0.1, "pumpkin": 0.05, "eggplant": 0.05, "carrot": 0.05},
    "soy": {"tofu": 0.5, "oil": 0.25, "onion": 0.1, "tomato": 0.15},
    "veg_curry": {"oil": 0.4, "onion": 0.12, "tomato": 0.12, "potato": 0.12, "cauliflower": 0.06, "green_beans": 0.06, "carrot": 0.06, "green_peas": 0.06},
    "leafy": {"spinach": 0.2, "oil": 0.4, "onion": 0.1, "tomato": 0.1, "paneer": 0.1, "potato": 0.1},
    "saag": {"mustard_greens": 0.2, "spinach": 0.1, "oil": 0.4, "onion": 0.1, "tomato": 0.1, "corn": 0.1},
    "okra": {"okra": 0.3, "oil": 0.5, "onion": 0.1, "tomato": 0.1},
    "brinjal": {"eggplant": 0.3, "oil": 0.45, "onion": 0.1, "tomato": 0.1, "peanut": 0.05},
    "cabbage": {"cabbage": 0.3, "oil": 0.45, "carrot": 0.1, "green_peas": 0.1, "onion": 0.05},
    "gobi": {"cauliflower": 0.3, "oil": 0.45, "potato": 0.1, "onion": 0.075, "tomato": 0.075},
    "aloo": {"potato": 0.5, "oil": 0.35, "onion": 0.075, "tomato": 0.075},
    "peas": {"green_peas": 0.4, "oil": 0.3, "onion": 0.1, "tomato": 0.1, "potato": 0.1},
    "mushroom": {"mushroom": 0.25, "oil": 0.45, "onion": 0.15, "tomato": 0.15},
    "capsicum": {"capsicum": 0.25, "oil": 0.45, "onion": 0.15, "tomato": 0.15},
    "gourd": {"gourd": 0.3, "oil": 0.45, "onion": 0.1, "tomato": 0.15},
    "bitter_gourd": {"bitter_gourd": 0.3, "oil": 0.45, "onion": 0.15, "sesame": 0.1},
    "drumstick": {"drumstick": 0.25, "oil": 0.4, "onion": 0.15, "tomato": 0.2},
    "pumpkin": {"pumpkin": 0.4, "oil": 0.35, "onion": 0.1, "tomato": 0.15},
    "corn": {"corn": 0.5, "oil": 0.3, "onion": 0.1, "tomato": 0.1},
    "sweet_potato": {"sweet_potato": 0.7, "oil": 0.2, "onion": 0.1},
    "beans": {"green_beans": 0.35, "oil": 0.4, "onion": 0.1, "tomato": 0.15},
    "carrot": {"carrot": 0.35, "oil": 0.4, "onion": 0.1, "green_peas": 0.15},
    "greens_mixed": {"beet_greens": 0.2, "oil": 0.4, "onion": 0.2, "lentil": 0.2},
    "rice": {"rice_white": 0.95, "oil": 0.05},
    "rice_brown": {"rice_brown": 1.0},
    "rice_dish": {"rice_white": 0.6, "oil": 0.25, "onion": 0.05, "carrot": 0.05, "green_peas": 0.05},
    "curd_rice": {"rice_white": 0.6, "yogurt": 0.35, "oil": 0.05},
    "biryani_chicken": {"rice_white": 0.5, "chicken": 0.2, "oil": 0.2, "onion": 0.05, "yogurt": 0.05},
    "biryani_mutton": {"rice_white": 0.5, "lamb": 0.2, "oil": 0.2, "onion": 0.05, "yogurt": 0.05},
    "biryani_egg": {"rice_white": 0.5, "egg": 0.15, "oil": 0.25, "onion": 0.05, "yogurt": 0.05},
    "biryani_veg": {"rice_white": 0.6, "oil": 0.25, "carrot": 0.05, "green_peas": 0.05, "potato": 0.05},
    "biryani_fish": {"rice_white": 0.5, "fish": 0.2, "oil": 0.2, "onion": 0.05, "yogurt": 0.05},
    "khichdi": {"rice_white": 0.45, "mung": 0.35, "ghee": 0.15, "onion": 0.05},
    "roti": {"wheat_flour": 0.9, "ghee": 0.1},
    "roti_plain": {"wheat_flour": 1.0},
    "paratha": {"wheat_flour": 0.6, "oil": 0.3, "potato": 0.1},
    "bread_white": {"bread_white": 0.8, "oil": 0.1, "milk": 0.1},
    "bread_whole": {"bread_whole": 1.0},
    "millet": {"millet": 0.85, "oil": 0.1, "onion": 0.05},
    "ragi": {"sorghum": 0.85, "oil": 0.1, "milk": 0.05},
    "oats": {"oats": 0.8, "milk": 0.2},
    "idli": {"rice_white": 0.6, "lentil": 0.3, "oil": 0.1},
    "dosa": {"rice_white": 0.5, "lentil": 0.2, "oil": 0.3},
    "upma_poha": {"rice_white": 0.55, "oil": 0.25, "peanut": 0.08, "onion": 0.07, "carrot": 0.05},
    "egg_plain": {"egg": 0.75, "oil": 0.25},
    "egg_curry": {"egg": 0.45, "oil": 0.3, "onion": 0.1, "tomato": 0.15},
    "chicken": {"chicken": 0.5, "oil": 0.35, "onion": 0.08, "tomato": 0.07},
    "mutton": {"lamb": 0.55, "oil": 0.3, "onion": 0.08, "tomato": 0.07},
    "fish": {"fish": 0.5, "oil": 0.35, "onion": 0.08, "tomato": 0.07},
    "prawn": {"shrimp": 0.5, "oil": 0.35, "onion": 0.08, "tomato": 0.07},
    "paneer": {"paneer": 0.5, "oil": 0.25, "onion": 0.1, "tomato": 0.1, "yogurt": 0.05},
    "milk": {"milk": 1.0},
    "curd": {"yogurt": 1.0},
    "lassi": {"yogurt": 0.8, "sugar": 0.2},
    "milk_sweet": {"milk": 0.5, "sugar": 0.3, "rice_white": 0.1, "cashew": 0.1},
    "sweet": {"sugar": 0.35, "wheat_flour": 0.2, "ghee": 0.3, "milk": 0.15},
    "sweet_jaggery": {"jaggery": 0.3, "wheat_flour": 0.25, "ghee": 0.3, "peanut": 0.15},
    "snack_fried": {"wheat_flour": 0.35, "potato": 0.15, "oil": 0.45, "onion": 0.05},
    "snack_chickpea": {"chickpea": 0.45, "oil": 0.4, "onion": 0.1, "tomato": 0.05},
    "chaat": {"potato": 0.25, "chickpea": 0.2, "wheat_flour": 0.2, "oil": 0.25, "tomato": 0.05, "onion": 0.05},
    "salad": {"cucumber": 0.15, "tomato": 0.2, "onion": 0.15, "carrot": 0.15, "oil": 0.2, "chickpea": 0.15},
    "smoothie": {"milk": 0.5, "banana": 0.5},
    "fruit_mixed": {"banana": 0.25, "apple": 0.2, "orange": 0.2, "papaya": 0.15, "guava": 0.2},
    "thali": {"rice_white": 0.3, "wheat_flour": 0.1, "lentil": 0.15, "oil": 0.2, "yogurt": 0.1, "potato": 0.05, "onion": 0.05, "tomato": 0.05},
    "nuts_mixed": {"almond": 0.3, "cashew": 0.25, "peanut": 0.2, "walnut": 0.15, "pistachio": 0.1},
}
for _fruit in ("banana", "apple", "mango", "orange", "papaya", "guava", "grapes", "watermelon", "pineapple", "pomegranate", "coconut", "dates"):
    PROFILES[f"fruit_{_fruit}"] = {_fruit: 1.0}
for _nut in ("almond", "cashew", "peanut", "walnut", "pistachio", "sesame", "flaxseed"):
    PROFILES[f"nut_{_nut}"] = {_nut: 1.0}

# Words in a food name that decide its profile. The first rule that matches wins, so specific rules come first.
# "NONE" means not tracked: packaged and processed foods, soft drinks, tea and coffee, alcohol.
NONE = "NONE"
KEYWORD_PROFILES: List[tuple] = [
    (NONE, ["beer", "wine", "whisky", "whiskey", "rum", "vodka", "gin", "brandy", "cocktail", "mojito", "cola", "pepsi", "soda", "soft drink", "energy drink", "tea", "coffee",
            "cappuccino", "latte", "espresso", "chocolate", "biscuit", "cookie", "chips", "namkeen", "maggi", "instant", "noodles", "pasta", "pizza", "burger", "fries", "cake",
            "ice cream", "cereal", "cornflakes", "muffin", "donut", "doughnut", "pastry", "protein bar", "protein shake", "sugarcane", "juice", "water", "pickle", "sauce", "chutney"]),
    ("biryani_chicken", ["chicken biryani", "chicken pulao", "chicken fried rice"]),
    ("biryani_mutton", ["mutton biryani", "mutton pulao", "haleem", "mandi rice with mutton"]),
    ("biryani_egg", ["egg biryani", "egg fried rice"]),
    ("biryani_fish", ["fish biryani", "prawn biryani"]),
    ("biryani_veg", ["biryani", "pulao", "pulav", "fried rice"]),
    ("curd_rice", ["curd rice", "dahi chawal", "dahi rice", "thayir", "perugu annam"]),
    ("khichdi", ["khichdi", "pongal"]),
    ("idli", ["idli", "idly"]),
    ("dosa", ["dosa", "uttapam", "uthappam", "appam", "pesarat", "adai"]),
    ("upma_poha", ["upma", "poha", "pohe", "puttu", "semiya", "vermicelli", "sevai", "sevaiya"]),
    ("paratha", ["paratha", "thepla", "puri", "poori", "bhatura", "kulcha", "naan"]),
    ("roti", ["roti", "chapati", "phulka", "bhakri", "rotla"]),
    ("snack_chickpea", ["murukku", "chakli", "bhujia", "sev", "mixture", "roasted chana", "pakora", "pakoda", "bajji", "bonda", "vada", "vadai", "falafel"]),
    ("snack_fried", ["samosa", "kachori", "cutlet", "tikki", "spring roll", "puff", "fritter", "mirchi"]),
    ("chaat", ["chaat", "bhel", "pani puri", "golgappa", "sev puri", "dahi puri", "pav bhaji"]),
    ("thali", ["thali", "canteen lunch", "baati", "full meals"]),
    ("prawn", ["prawn", "shrimp"]),
    ("fish", ["fish", "pomfret", "rohu", "salmon", "sardine", "mackerel", "tuna", "crab"]),
    ("mutton", ["mutton", "lamb", "keema", "goat", "gosht"]),
    ("saag", ["saag", "sarson", "mustard"]),
    ("leafy", ["palak", "spinach", "methi", "thotakura", "gongura", "greens", "leaf", "keerai"]),
    ("paneer", ["paneer"]),
    ("chicken", ["chicken", "tandoori", "tikka"]),
    ("egg_curry", ["egg curry", "egg masala", "egg bhurji", "anda"]),
    ("egg_plain", ["egg", "omelette", "omelet"]),
    ("paneer", ["cheese"]),
    ("lassi", ["lassi", "buttermilk", "chaas", "mor", "raita"]),
    ("curd", ["curd", "yogurt", "yoghurt", "dahi"]),
    ("smoothie", ["smoothie", "milkshake", "shake"]),
    ("milk_sweet", ["kheer", "payasam", "payasa", "phirni", "rasmalai", "rabdi", "kulfi"]),
    ("milk", ["milk"]),
    ("rajma", ["rajma", "kidney bean"]),
    ("chana", ["chana", "chole", "chickpea", "sundal", "hummus"]),
    ("lobia", ["lobia", "cowpea", "black eyed"]),
    ("dal_mung", ["moong", "mung", "pesarattu"]),
    ("sambar", ["sambar", "sambhar", "rasam"]),
    ("dal", ["dal", "daal", "tadka", "lentil", "pappu", "kootu"]),
    ("soy", ["soya", "soy", "tofu"]),
    ("okra", ["okra", "bhindi", "ladies finger", "dondakaya"]),
    ("brinjal", ["brinjal", "baingan", "eggplant", "vankaya", "bharta"]),
    ("cabbage", ["cabbage"]),
    ("gobi", ["gobi", "cauliflower", "broccoli"]),
    ("aloo", ["aloo", "potato", "batata", "urulai"]),
    ("peas", ["matar", "peas", "mutter"]),
    ("mushroom", ["mushroom"]),
    ("capsicum", ["capsicum", "bell pepper", "shimla"]),
    ("bitter_gourd", ["bitter gourd", "karela", "kakarakaya"]),
    ("gourd", ["gourd", "lauki", "dudhi", "sorakaya", "tinda", "tori", "ridge"]),
    ("drumstick", ["drumstick", "moringa"]),
    ("pumpkin", ["pumpkin", "kaddu"]),
    ("corn", ["corn", "bhutta"]),
    ("sweet_potato", ["sweet potato"]),
    ("beans", ["beans", "french bean"]),
    ("carrot", ["carrot", "beetroot", "beet"]),
    ("oats", ["oats", "oatmeal", "porridge", "dalia", "daliya"]),
    ("ragi", ["ragi", "finger millet"]),
    ("millet", ["millet", "jowar", "bajra", "quinoa", "barley", "korra", "samai"]),
    ("bread_whole", ["whole wheat bread", "brown bread", "multigrain bread"]),
    ("bread_white", ["bread", "toast", "sandwich", "bun", "pav"]),
    ("rice_brown", ["brown rice"]),
    ("rice", ["steamed rice", "plain rice", "white rice", "boiled rice", "cooked rice", "rice (", "annam"]),
    ("rice_dish", ["rice", "bath", "pulihora", "tamarind rice", "lemon rice", "tomato rice", "jeera rice"]),
    ("sweet_jaggery", ["jaggery", "laddu", "ladoo", "chikki", "bellam", "sundaulu"]),
    ("sweet", ["halwa", "barfi", "burfi", "jalebi", "gulab", "rasgulla", "peda", "sweet", "mithai", "kaja", "mysore pak", "badusha", "sheera", "kesari", "malpua"]),
    ("salad", ["salad", "kachumber", "sprouts", "raita"]),
    ("fruit_banana", ["banana"]),
    ("fruit_apple", ["apple"]),
    ("fruit_mango", ["mango"]),
    ("fruit_orange", ["orange", "mosambi", "sweet lime", "lemon", "kinnow"]),
    ("fruit_papaya", ["papaya"]),
    ("fruit_guava", ["guava", "amrud", "jamun", "amla", "sapota", "chikoo", "custard apple", "sitaphal"]),
    ("fruit_grapes", ["grape", "berries", "berry"]),
    ("fruit_watermelon", ["watermelon", "muskmelon", "melon"]),
    ("fruit_pineapple", ["pineapple"]),
    ("fruit_pomegranate", ["pomegranate", "anar"]),
    ("fruit_coconut", ["coconut"]),
    ("fruit_dates", ["dates", "date ", "anjeer", "fig", "raisin", "dry fruit"]),
    ("nut_almond", ["almond", "badam"]),
    ("nut_cashew", ["cashew", "kaju"]),
    ("nut_peanut", ["peanut", "groundnut"]),
    ("nut_walnut", ["walnut", "akhrot"]),
    ("nut_pistachio", ["pistachio", "pista"]),
    ("nut_sesame", ["sesame", "til "]),
    ("nut_flaxseed", ["flax", "chia", "seeds"]),
    ("nuts_mixed", ["nuts", "trail mix"]),
]
CATEGORY_PROFILES: Dict[str, Optional[str]] = {
    "vegetable curries": "veg_curry", "dal & sambar": "dal", "rice & mains": "rice_dish", "roti & bread": "roti", "tiffin": "idli",
    "dairy & paneer": "paneer", "eggs": "egg_curry", "chicken": "chicken", "mutton": "mutton", "fish & seafood": "fish",
    "salads & light meals": "salad", "fruits": "fruit_mixed", "nuts & seeds": "nuts_mixed", "millets & grains": "millet",
    "sweets": "sweet", "snacks": "snack_chickpea", "drinks": None, "alcohol": None,
}


def _word_match(words: List[str], text: str) -> bool:
    return any(re.search(r"(?<![a-z])" + re.escape(word.strip()) + r"(?:s|es)?(?![a-z])", text) for word in words)


def profile_for(name: str, category: Optional[str] = None) -> Optional[str]:
    """The profile name for a food, or None when it is not tracked."""
    text = f" {name} ".lower()
    for profile, words in KEYWORD_PROFILES:
        if _word_match(words, text):
            return None if profile == NONE else profile
    if category:
        return CATEGORY_PROFILES.get(category.lower())
    return None


def per_kcal(profile: str) -> Dict[str, float]:
    """Amount of each nutrient per 1 kcal of a food that follows this profile."""
    shares = PROFILES[profile]
    return {key: sum(share * _BASES[base]["per_100kcal"][key] for base, share in shares.items()) / 100 for key in KEYS}


def estimate(name: str, calories: float, category: Optional[str] = None) -> Optional[Dict[str, float]]:
    """Nutrients in a serving of `calories` kcal named `name`; None when we cannot estimate it (shown as "not tracked")."""
    profile = profile_for(name, category)
    if profile is None or calories <= 0:
        return None
    rates = per_kcal(profile)
    return {key: round(rates[key] * calories, 2 if key in ("iron", "zinc", "vitamin_e", "vitamin_b12") else 1) for key in KEYS}


def implied_grams(profile: str, calories: float) -> Dict[str, float]:
    """Weight of each base food a serving of this profile would hold: used to check the profiles are plausible."""
    return {base: share * calories / _BASES[base]["kcal_per_100g"] * 100 for base, share in PROFILES[profile].items()}


def reference_amounts(sex: Optional[str]) -> Dict[str, Optional[float]]:
    """Daily reference per nutrient for an adult. 'Male' / 'Female' use their own row; anything else uses the lower of the two."""
    out: Dict[str, Optional[float]] = {}
    for key in KEYS:
        row = RDA["nutrients"].get(key, {})
        male, female = row.get("male"), row.get("female")
        if sex == "Male":
            value = male
        elif sex == "Female":
            value = female
        else:
            values = [item for item in (male, female) if item is not None]
            value = min(values) if values else None
        out[key] = value
    return out


def summarise(meals: List[Dict[str, Any]], sex: Optional[str], catalogue_category) -> List[Dict[str, Any]]:
    """Totals so far for a list of logged meals, one entry per nutrient: total, reference, percent, tracked and how many meals counted."""
    totals = {key: 0.0 for key in KEYS}
    counted = 0
    for meal in meals:
        found = estimate(str(meal.get("name") or ""), float(meal.get("calories") or 0), catalogue_category(str(meal.get("name") or "")))
        if found is None:
            continue
        counted += 1
        for key in KEYS:
            totals[key] += found[key]
    reference = reference_amounts(sex)
    result = []
    for item in NUTRIENTS:
        key = item["key"]
        ref = reference.get(key)
        total = round(totals[key], 2 if key in ("iron", "zinc", "vitamin_e", "vitamin_b12") else 1)
        result.append({
            "key": key, "en": item["en"], "te": item["te"], "unit": item["unit"], "total": total, "reference": ref, "tracked": counted > 0, "meals_counted": counted,
            "percent": round(total / ref * 100) if ref and counted else None, "limit": key in LIMIT_NUTRIENTS,
        })
    return result


# Foods generally known to be good sources, for "what in your kitchen could help" (rule-based; names as in our ingredient list).
RICH_IN: Dict[str, List[str]] = {
    "iron": ["spinach", "palak", "methi", "fenugreek", "amaranth", "rajma", "kidney bean", "chickpea", "chana", "lentil", "dal", "dates", "sesame", "beetroot", "ragi", "jaggery"],
    "calcium": ["milk", "curd", "yogurt", "paneer", "ragi", "sesame", "almond", "tofu", "drumstick"],
    "zinc": ["chickpea", "chana", "rajma", "lentil", "dal", "cashew", "sesame", "egg", "chicken", "mutton", "milk"],
    "magnesium": ["almond", "cashew", "peanut", "spinach", "palak", "ragi", "oats", "millet", "pumpkin"],
    "potassium": ["banana", "potato", "sweet potato", "spinach", "palak", "tomato", "beans", "lentil", "dal"],
    "vitamin_a": ["carrot", "sweet potato", "spinach", "palak", "pumpkin", "mango", "papaya", "drumstick", "egg", "milk"],
    "vitamin_b12": ["milk", "curd", "yogurt", "paneer", "egg", "fish", "chicken", "mutton"],
    "folate": ["spinach", "palak", "methi", "fenugreek", "lentil", "dal", "chickpea", "chana", "beans", "peas", "orange"],
    "vitamin_c": ["amla", "guava", "orange", "lemon", "tomato", "capsicum", "papaya"],
    "vitamin_d": ["egg", "fish", "milk", "mushroom"],
    "vitamin_e": ["almond", "peanut", "sesame", "sunflower", "spinach", "palak"],
    "vitamin_k": ["spinach", "palak", "methi", "fenugreek", "cabbage", "broccoli", "mustard", "drumstick"],
}


def rich_matches(nutrient: str, names: List[str], limit: int = 3) -> List[str]:
    """Which of these (kitchen) ingredient names are good sources of the nutrient. Order of RICH_IN decides, so the best sources come first."""
    lowered = [(name, f" {name.lower()} ") for name in names]
    found: List[str] = []
    for word in RICH_IN.get(nutrient, []):
        for name, text in lowered:
            if name not in found and re.search(r"(?<![a-z])" + re.escape(word) + r"(?:s|es)?(?![a-z])", text):
                found.append(name)
    return found[:limit]


def weekly(days: Dict[str, List[Dict[str, Any]]], sex: Optional[str], catalogue_category) -> Dict[str, Any]:
    """7-day average per nutrient over the days that have any tracked food, and the nutrients that are often low.
    `days` maps a date to that day's logged meals. A nutrient is 'often low' when its average is under half the reference, on 3 or more days with food logged."""
    per_day = {date: summarise(meals, sex, catalogue_category) for date, meals in days.items()}
    logged = [date for date, rows in per_day.items() if rows and rows[0]["tracked"]]
    reference = reference_amounts(sex)
    nutrients_out, often_low = [], []
    for item in NUTRIENTS:
        key = item["key"]
        totals = [next(row for row in per_day[date] if row["key"] == key)["total"] for date in logged]
        average = round(sum(totals) / len(totals), 2) if totals else None
        ref = reference.get(key)
        percent = round(average / ref * 100) if (average is not None and ref) else None
        nutrients_out.append({"key": key, "en": item["en"], "te": item["te"], "unit": item["unit"], "average": average, "reference": ref, "percent": percent, "limit": key in LIMIT_NUTRIENTS})
        if key not in LIMIT_NUTRIENTS and percent is not None and percent < 50 and len(logged) >= 3:
            often_low.append(key)
    return {"days_logged": len(logged), "nutrients": nutrients_out, "often_low": often_low}
