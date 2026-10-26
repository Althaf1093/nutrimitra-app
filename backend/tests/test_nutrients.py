"""Nutrients PR 2: vitamins and minerals. Data checks, the estimator, the reference amounts, the dashboard totals and the weekly view."""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import foods  # noqa: E402
import nutrients  # noqa: E402
from test_kitchen_daily import log  # noqa: E402
from test_kitchen_plan import auth, person, stack  # noqa: E402,F401  (stack is a fixture)

DATA = Path(__file__).resolve().parents[1] / "data"


def test_every_base_food_has_every_nutrient_and_a_usda_source():
    doc = json.loads((DATA / "nutrients.json").read_text(encoding="utf-8"))
    assert "USDA" in doc["source"] and "CC0" in doc["source"]
    assert len(doc["bases"]) >= 60
    for key, base in doc["bases"].items():
        assert base["fdc_id"] and base["description"] and base["kcal_per_100g"] > 0, key
        assert set(base["per_100kcal"]) == set(nutrients.KEYS), key
        assert all(value >= 0 for value in base["per_100kcal"].values()), key


def test_profiles_use_known_bases_and_their_shares_add_up():
    for name, shares in nutrients.PROFILES.items():
        assert set(shares) <= set(nutrients._BASES), name
        assert abs(sum(shares.values()) - 1) < 0.011, (name, sum(shares.values()))


def test_profiles_imply_plausible_weights_for_every_catalogue_food():
    """A serving never holds more than 700 g of one base food (a check that energy shares are not inflating low-calorie vegetables)."""
    for food in foods.catalogue.foods:
        profile = nutrients.profile_for(food.raw["name"], food.raw["category"])
        if profile is None:
            continue
        for base, grams in nutrients.implied_grams(profile, food.raw["calories"]).items():
            assert grams <= 700, (food.raw["name"], profile, base, round(grams))


def test_most_foods_are_tracked_and_drinks_alcohol_and_packaged_foods_are_not():
    tracked = [food for food in foods.catalogue.foods if nutrients.profile_for(food.raw["name"], food.raw["category"]) is not None]
    assert len(tracked) / len(foods.catalogue.foods) >= 0.7
    for name in ("Masala tea (with milk and sugar)", "Maggi noodles (vegetable)"):
        food = foods.catalogue.find_by_name(name)
        assert food, name
        assert nutrients.estimate(food.raw["name"], food.raw["calories"], food.raw["category"]) is None, name  # None, never zeros
    alcohol = [food for food in foods.catalogue.foods if food.raw["category"] == "Alcohol"]
    assert alcohol and all(nutrients.estimate(food.raw["name"], max(food.raw["calories"], 1), food.raw["category"]) is None for food in alcohol)


def test_estimates_follow_the_food():
    rajma = nutrients.estimate("Rajma masala", 350, "Dal & sambar")
    rice = nutrients.estimate("Steamed rice", 350, "Rice & mains")
    spinach = nutrients.estimate("Palak paneer", 300, "Dairy & paneer")
    milk = nutrients.estimate("Milk", 150, "Dairy & paneer")
    egg = nutrients.estimate("Boiled egg", 156, "Eggs")
    assert rajma["iron"] > rice["iron"] * 2 and rajma["folate"] > rice["folate"]
    assert spinach["vitamin_k"] > 100 and spinach["vitamin_a"] > 50
    assert milk["calcium"] > 200 and milk["vitamin_b12"] > 0.5
    assert egg["vitamin_b12"] > 0.5 and egg["vitamin_d"] > 0
    assert nutrients.estimate("Rajma masala", 0, "Dal & sambar") is None


def test_reference_amounts_by_sex_and_the_source_is_written_down():
    rda = json.loads((DATA / "rda.json").read_text(encoding="utf-8"))
    assert "ICMR-NIN" in rda["source"] and rda["year"] == 2020
    assert set(rda["nutrients"]) == set(nutrients.KEYS)
    assert nutrients.reference_amounts("Male")["iron"] == 19 and nutrients.reference_amounts("Female")["iron"] == 29
    assert nutrients.reference_amounts("Prefer not to say")["iron"] == 19  # the lower of the two
    for key, row in rda["nutrients"].items():
        assert row["unit"] and "checked" in row, key


def test_every_nutrient_has_english_and_telugu_names_and_the_app_has_the_words():
    for item in nutrients.NUTRIENTS:
        assert item["en"] and item["te"] and item["unit"] and item["group"] in ("vitamin", "mineral")
    root = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n.ts"
    text = root.read_text(encoding="utf-8")
    for key in ("nutrientsTitle", "nutrientsNote", "nutrientsLowest", "nutrientsNone", "nutrientsWeekTitle", "nutrientsOftenLow", "nutrientsFromKitchen"):
        assert text.count(f"    {key}:") == 2, key
    own = [line.lower() for line in text.splitlines() if line.startswith("    nutrients")]
    assert len(own) >= 26
    for line in own:  # wording rules: general information only, no deficiency, treatment or supplement talk
        for word in ("deficien", "treat", "cure", "supplement", "dose", "disease"):
            assert word not in line, (word, line)


def test_dashboard_totals_and_untracked_meals(stack):
    _, url = stack
    token = person(url, None)
    empty = requests.get(f"{url}/api/dashboard", headers=auth(token), timeout=20).json()["nutrients"]
    assert [row["key"] for row in empty] == nutrients.KEYS and not any(row["tracked"] for row in empty)
    log(url, token, "Masala tea", meal_type="snack", calories=80, protein=2)
    tea_only = requests.get(f"{url}/api/dashboard", headers=auth(token), timeout=20).json()["nutrients"]
    assert not any(row["tracked"] for row in tea_only), "tea is not tracked, so nothing is counted and nothing is shown as zero"
    log(url, token, "Rajma masala", calories=350, protein=15)
    after = {row["key"]: row for row in requests.get(f"{url}/api/dashboard", headers=auth(token), timeout=20).json()["nutrients"]}
    assert after["iron"]["tracked"] and after["iron"]["total"] > 3 and after["iron"]["reference"] in (19, 29)
    assert after["iron"]["percent"] == round(after["iron"]["total"] / after["iron"]["reference"] * 100)
    assert after["sodium"]["limit"] is True and after["iron"]["limit"] is False
    assert after["iron"]["meals_counted"] == 1


def test_weekly_view_averages_and_names_what_is_often_low(stack):
    _, url = stack
    token = person(url, None)
    week = requests.get(f"{url}/api/nutrients/weekly", headers=auth(token), timeout=20).json()
    assert week["days_logged"] == 0 and week["often_low"] == [] and len(week["nutrients"]) == len(nutrients.KEYS)
    assert all(row["average"] is None for row in week["nutrients"])
    log(url, token, "Steamed rice", calories=300, protein=6)
    week = requests.get(f"{url}/api/nutrients/weekly", headers=auth(token), timeout=20).json()
    assert week["days_logged"] == 1 and week["often_low"] == [], "needs 3 days with food before anything is called often low"
    assert next(row for row in week["nutrients"] if row["key"] == "iron")["average"] > 0


def test_weekly_often_low_needs_three_days_and_never_lists_sodium():
    meals = {f"2026-10-0{day}": [{"name": "Steamed rice", "calories": 300}] for day in range(1, 5)}
    week = nutrients.weekly(meals, "Female", lambda name: None)
    assert week["days_logged"] == 4 and "iron" in week["often_low"] and "vitamin_b12" in week["often_low"]
    assert "sodium" not in week["often_low"]


def test_kitchen_suggestions_pick_good_sources_from_what_the_person_has():
    assert nutrients.rich_matches("iron", ["Rice", "Palak (spinach)", "Onion", "Rajma"]) == ["Palak (spinach)", "Rajma"]
    assert nutrients.rich_matches("vitamin_b12", ["Rice", "Tomato"]) == []
    assert nutrients.rich_matches("vitamin_c", ["Guava", "Amla", "Rice"], limit=1) == ["Amla"]
