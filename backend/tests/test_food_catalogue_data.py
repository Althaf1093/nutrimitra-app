"""Logging run item 3: the big food and drink catalogue (data/foods.json plus data/foods/*.txt). Pure data checks, no server."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import foods  # noqa: E402

COMPACT = Path(__file__).resolve().parents[1] / "data" / "foods"


@pytest.fixture(scope="module")
def catalogue():
    return foods.catalogue


def test_catalogue_has_2500_plus_foods(catalogue):
    assert len(catalogue.foods) >= 2500


def test_ids_and_names_are_unique(catalogue):
    ids = [food.id for food in catalogue.foods]
    names = [food.name_norm for food in catalogue.foods]
    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))


def test_every_row_has_the_required_fields_and_sane_numbers(catalogue):
    for food in catalogue.foods:
        raw = food.raw
        assert raw["name"] and raw["category"] and raw["serving"], food.id
        for key in ("calories", "protein_g", "carbs_g", "fat_g"):
            assert isinstance(raw[key], (int, float)) and raw[key] >= 0, (food.id, key)
        assert raw["calories"] <= 1500, food.id
        assert food.serving_options(), food.id


def test_macros_are_consistent_with_calories(catalogue):
    """Calories must follow from protein, carbs, fat (and alcohol, 7 kcal/g) within a tolerance; the hand-written rows were rounded."""
    bad = []
    for food in catalogue.foods:
        raw = food.raw
        expected = 4 * raw["protein_g"] + 4 * raw["carbs_g"] + 9 * raw["fat_g"] + 7 * raw.get("alcohol_g", 0)
        if raw["calories"] < 15 and expected < 15:
            continue
        if food.id in ("beer", "wine", "whisky-spirits"):
            continue  # the older generic rows (Beer, Wine, Whisky) carry the alcohol energy in calories only
        if abs(raw["calories"] - expected) > max(40, 0.35 * expected):
            bad.append((food.id, raw["calories"], round(expected)))
    assert not bad, bad[:20]


def test_compact_rows_are_exactly_consistent(catalogue):
    for food in catalogue.foods:
        raw = food.raw
        if not raw.get("estimate"):
            continue
        expected = round(4 * raw["protein_g"] + 4 * raw["carbs_g"] + 9 * raw["fat_g"] + 7 * raw.get("alcohol_g", 0))
        assert raw["calories"] == expected, food.id


def test_compact_files_have_ten_fields_and_no_stray_lines():
    for path in COMPACT.glob("*.txt"):
        if path.name.lower() == "readme.txt":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("|")
            assert len(parts) == 10, f"{path.name}:{number} has {len(parts)} fields: {line[:60]}"
            for value in parts[4:9]:
                float(value or 0)


@pytest.mark.parametrize("query", ["masala tea", "green tea", "beer", "whisky", "ragi dosa", "biryani", "rum", "vodka", "wine", "coffee", "lassi", "buttermilk", "coconut water", "sugarcane juice", "cappuccino", "cold coffee", "energy drink", "protein shake", "mojito", "haleem", "pesarattu", "pav bhaji"])
def test_search_finds_common_foods_and_drinks(catalogue, query):
    assert catalogue.search(query, 10), query


def test_drinks_are_in_ml_and_alcohol_is_neutral(catalogue):
    alcohol = [food for food in catalogue.foods if food.raw["category"] == "Alcohol"]
    assert len(alcohol) >= 50
    for food in alcohol:
        assert "ml" in food.raw["serving"] or "peg" in food.raw["serving"] or "glass" in food.raw["serving"] or "shot" in food.raw["serving"] or "pint" in food.raw["serving"] or "bottle" in food.raw["serving"] or "can" in food.raw["serving"] or "measure" in food.raw["serving"], food.id
    # Beer in both bottle sizes and spirits per 30 ml and 60 ml peg.
    names = " ".join(food.raw["name"] for food in alcohol).lower()
    for needed in ("330 ml", "650 ml", "30 ml", "60 ml", "wine"):
        assert needed in names


def test_search_results_label_values_as_estimates(catalogue):
    for item in catalogue.search("masala tea", 5):
        assert item["estimate"] is True


def test_the_original_file_is_untouched_and_the_count_adds_up(catalogue):
    original = len(json.loads((Path(__file__).resolve().parents[1] / "data" / "foods.json").read_text(encoding="utf-8"))["foods"])
    assert original == 589
    assert len(catalogue.foods) > original + 2000


def test_telugu_names_for_most_new_rows(catalogue):
    new = [food for food in catalogue.foods if food.raw.get("estimate")]
    assert sum(1 for food in new if food.raw.get("te")) >= 0.8 * len(new)


def test_every_row_has_an_estimated_fibre_that_fits_its_carbs(catalogue):
    """Fibre PR: all rows carry fibre_g (0 is allowed for meat, fish, eggs, oil, plain drinks), never more than the carbs, never negative."""
    for food in catalogue.foods:
        raw = food.raw
        assert "fibre_g" in raw, food.id
        assert isinstance(raw["fibre_g"], (int, float)) and 0 <= raw["fibre_g"] <= raw["carbs_g"], (food.id, raw["fibre_g"], raw["carbs_g"])
        assert food.public()["fibre_g"] == raw["fibre_g"]


def test_fibre_is_higher_in_plants_than_in_meat_and_drinks(catalogue):
    by_name = {food.name_norm: food.raw["fibre_g"] for food in catalogue.foods}
    assert by_name["rajma masala"] >= 8
    assert by_name["oats porridge milk"] >= 3
    assert max(food.raw["fibre_g"] for food in catalogue.foods if food.raw["category"] in ("Chicken", "Mutton", "Eggs")) <= 3
    assert all(food.raw["fibre_g"] == 0 for food in catalogue.foods if food.raw["category"] == "Alcohol")
