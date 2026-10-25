"""Feature 1, item 1: the ingredient catalogue and the kitchen profile (GET/PUT /api/kitchen), diet filtering, deletion and export."""
import json
import re
from pathlib import Path

import pytest
import requests

import kitchen
from conftest import p4_signup

DATA = Path(__file__).resolve().parents[1] / "data" / "ingredients.json"
TELUGU_LETTER = re.compile("[ఀ-౿]")
PROFILE = {"age": 30, "sex": "Prefer not to say", "height_cm": 170, "weight_kg": 70, "target_weight_kg": 65, "conditions": [], "dietary_preferences": ["Vegetarian"], "allergies": [], "disliked_foods": [], "activity_level": "Moderately active", "cooking_time": "20–30 min", "food_budget": "Balanced", "wellness_goal": "Healthier living", "language": "en", "timezone": "Asia/Kolkata"}


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def person(p4, onboarded=True, **profile):
    """A signed-up person; unless onboarded=False they have a profile (the defaults above, overridden by `profile`)."""
    response, _ = p4_signup(p4)
    token = response.json()["token"]
    if onboarded:
        assert requests.put(f"{p4.url}/api/profile", json={**PROFILE, **profile}, headers=auth(token), timeout=20).status_code == 200
    return token


def catalogue(p4, token, **params):
    response = requests.get(f"{p4.url}/api/kitchen/ingredients", params=params, headers=auth(token), timeout=20)
    assert response.status_code == 200, response.text
    return response.json()["ingredients"]


def ids(items):
    return {item["id"] for item in items}


def put(p4, token, **body):
    return requests.put(f"{p4.url}/api/kitchen", json=body, headers=auth(token), timeout=20)


# ---- the data file ---------------------------------------------------------------------------------------------

def test_catalogue_is_a_data_file_with_english_and_telugu_names():
    data = json.loads(DATA.read_text(encoding="utf-8"))["ingredients"]
    assert len(data) >= 150
    assert len({item["id"] for item in data}) == len(data)
    for item in data:
        assert item["name"].strip() and item["group"] in kitchen.GROUPS and item["diet"] in kitchen.DIET_RANK, item["id"]
        assert TELUGU_LETTER.search(item["te"]), f"{item['id']} needs a Telugu name"
    groups = {}
    for item in data:
        groups.setdefault(item["group"], []).append(item["id"])
    assert len(groups["vegetables"]) + len(groups["leafy"]) >= 60
    vegetables = set(groups["vegetables"]) | set(groups["leafy"])
    for needed in ("brinjal", "okra", "tomato", "onion", "potato", "cabbage", "cauliflower", "beans", "carrot", "drumstick", "gongura", "spinach", "capsicum", "pumpkin", "beetroot", "raw-banana"):
        assert needed in vegetables, needed
    for needed in ("rice", "wheat-flour", "ragi", "jowar", "bajra", "oats", "foxtail-millet"):
        assert needed in groups["staples"], needed
    for needed in ("egg", "chicken", "fish", "paneer", "tofu"):
        assert needed in groups["protein"], needed
    assert {"curd", "milk"} <= set(groups["dairy"]) and "ghee" in groups["oils"] and "sprouts" in groups["pulses"] and "soya-chunks" in groups["pulses"]


def test_server_does_not_hardcode_the_ingredient_list():
    source = (Path(__file__).resolve().parents[1] / "server.py").read_text(encoding="utf-8")
    assert "Gongura" not in source and "Ladies finger" not in source


# ---- diet filtering --------------------------------------------------------------------------------------------

MEAT = {"chicken", "mutton", "fish", "prawns", "crab", "dried-fish"}


def test_a_vegetarian_never_sees_meat_fish_or_egg(p4):
    shown = ids(catalogue(p4, person(p4, dietary_preferences=["Vegetarian"])))
    assert not (shown & (MEAT | {"egg"}))
    assert {"paneer", "curd", "ghee", "milk", "tofu", "brinjal"} <= shown


def test_an_eggetarian_sees_egg_but_not_meat(p4):
    shown = ids(catalogue(p4, person(p4, dietary_preferences=["Eggetarian"])))
    assert "egg" in shown and not (shown & MEAT)


def test_a_vegan_sees_no_animal_products(p4):
    shown = ids(catalogue(p4, person(p4, dietary_preferences=["Vegan"])))
    assert not (shown & (MEAT | {"egg", "paneer", "curd", "milk", "ghee", "butter", "honey", "cheese", "buttermilk", "greek-yogurt"}))
    assert {"tofu", "rice", "toor-dal"} <= shown


def test_a_non_vegetarian_sees_everything(p4):
    shown = ids(catalogue(p4, person(p4, dietary_preferences=["Non-vegetarian"])))
    assert MEAT | {"egg", "paneer"} <= shown
    assert len(shown) == len(kitchen.catalogue.items)


def test_the_strictest_preference_wins(p4):
    shown = ids(catalogue(p4, person(p4, dietary_preferences=["Non-vegetarian", "Vegetarian"])))
    assert not (shown & MEAT)


def test_allergies_and_dislikes_are_hidden_too(p4):
    shown = ids(catalogue(p4, person(p4, dietary_preferences=["Non-vegetarian"], allergies=["peanut"], disliked_foods=["brinjal", "Prawns"])))
    assert not (shown & {"peanuts", "peanut-butter", "groundnut-oil", "brinjal", "prawns"})
    assert {"chicken", "almonds"} <= shown


def test_diet_and_exclude_parameters_stand_in_for_a_profile_that_does_not_exist_yet(p4):
    token = person(p4, onboarded=False)
    assert MEAT <= ids(catalogue(p4, token)), "no preference known: nothing is hidden"
    assert not (ids(catalogue(p4, token, diet="Vegetarian")) & MEAT)
    assert "peanuts" not in ids(catalogue(p4, token, diet="Vegetarian", exclude="peanut,brinjal"))


def test_search_finds_by_english_alias_and_plural(p4):
    token = person(p4, dietary_preferences=["Non-vegetarian"])
    assert "brinjal" in ids(catalogue(p4, token, q="vankaya")) and "brinjal" in ids(catalogue(p4, token, q="eggplant"))
    assert "okra" in ids(catalogue(p4, token, q="bhindi"))
    assert "egg" in ids(catalogue(p4, token, q="eggs"))
    assert catalogue(p4, token, q="zzzz") == []


# ---- GET / PUT /api/kitchen ------------------------------------------------------------------------------------

def test_a_new_person_has_no_kitchen_yet(p4):
    token = person(p4)
    assert requests.get(f"{p4.url}/api/kitchen", headers=auth(token), timeout=20).json() == {"configured": False, "kitchen": None}


def test_save_and_read_back_a_kitchen(p4):
    token = person(p4, dietary_preferences=["Vegetarian"])
    saved = put(p4, token, items=["rice", "toor-dal", "tomato", "onion", "paneer", "rice"], meals_per_day=2, household_size=4, cooking_time="Under 15 min")
    assert saved.status_code == 200, saved.text
    body = requests.get(f"{p4.url}/api/kitchen", headers=auth(token), timeout=20).json()
    assert body["configured"] is True
    kept = body["kitchen"]
    assert kept["items"] == ["rice", "toor-dal", "tomato", "onion", "paneer"], "duplicates dropped, order kept"
    assert (kept["meals_per_day"], kept["household_size"], kept["cooking_time"]) == (2, 4, "Under 15 min") and kept["updated_at"]
    again = put(p4, token, items=["rice"]).json()["kitchen"]
    assert again["items"] == ["rice"] and again["meals_per_day"] == 3 and again["household_size"] == 2, "defaults when not given"


def test_a_vegetarian_cannot_save_chicken(p4):
    token = person(p4, dietary_preferences=["Vegetarian"])
    response = put(p4, token, items=["rice", "chicken"])
    assert response.status_code == 422 and "Chicken" in response.json()["detail"]
    assert requests.get(f"{p4.url}/api/kitchen", headers=auth(token), timeout=20).json()["configured"] is False


def test_unknown_and_excluded_items_are_refused(p4):
    token = person(p4, dietary_preferences=["Non-vegetarian"], allergies=["peanut"])
    assert put(p4, token, items=["rice", "moon-cheese"]).status_code == 422
    assert put(p4, token, items=["peanuts"]).status_code == 422


@pytest.mark.parametrize("body", [
    {"items": [], "meals_per_day": 0}, {"items": [], "meals_per_day": 4}, {"items": [], "household_size": 0}, {"items": [], "household_size": 13},
    {"items": [], "cooking_time": "a long time"}, {"items": ["rice"] * (kitchen.MAX_ITEMS + 1)}, {"items": "rice"},
])
def test_bad_kitchen_values_are_refused(p4, body):
    assert put(p4, person(p4), **body).status_code == 422


def test_an_empty_kitchen_is_allowed(p4):
    token = person(p4)
    assert put(p4, token, items=[]).json()["kitchen"]["items"] == []


def test_items_that_no_longer_fit_a_changed_diet_are_not_shown(p4):
    token = person(p4, dietary_preferences=["Non-vegetarian"])
    assert put(p4, token, items=["rice", "chicken", "egg"]).status_code == 200
    assert requests.put(f"{p4.url}/api/profile", json={**PROFILE, "dietary_preferences": ["Vegetarian"]}, headers=auth(token), timeout=20).status_code == 200
    assert requests.get(f"{p4.url}/api/kitchen", headers=auth(token), timeout=20).json()["kitchen"]["items"] == ["rice"]


def test_each_person_has_their_own_kitchen(p4):
    one, two = person(p4), person(p4)
    put(p4, one, items=["rice", "ragi"])
    assert requests.get(f"{p4.url}/api/kitchen", headers=auth(two), timeout=20).json()["configured"] is False


@pytest.mark.parametrize("method,path", [("get", "/kitchen"), ("put", "/kitchen"), ("get", "/kitchen/ingredients"), ("get", "/account/export")])
def test_kitchen_endpoints_need_sign_in(p4, method, path):
    assert getattr(requests, method)(f"{p4.url}/api{path}", timeout=20).status_code == 401


# ---- deletion and export ---------------------------------------------------------------------------------------

def test_the_kitchen_is_removed_with_the_account(p4, p4db):
    response, _ = p4_signup(p4)
    token, user_id = response.json()["token"], response.json()["user"]["id"]
    put(p4, token, items=["rice"])
    assert p4db.kitchens.count_documents({"user_id": user_id}) == 1
    assert requests.delete(f"{p4.url}/api/account", json={"confirm": "DELETE", "password": "StrongPass123"}, headers=auth(token), timeout=20).status_code == 200
    assert p4db.kitchens.count_documents({"user_id": user_id}) == 0


def test_the_kitchen_collection_has_a_unique_index_on_the_user(p4, p4db):
    indexes = p4db.kitchens.index_information()
    assert any(info.get("unique") and info["key"] == [("user_id", 1)] for info in indexes.values()), indexes


def test_export_includes_the_kitchen_and_no_secrets(p4):
    token = person(p4, dietary_preferences=["Vegetarian"])
    put(p4, token, items=["rice", "toor-dal"], meals_per_day=2)
    assert requests.post(f"{p4.url}/api/meals", json={"meal_type": "lunch", "name": "Dal rice", "calories": 400, "protein_g": 12, "carbs_g": 60, "fat_g": 8}, headers=auth(token), timeout=20).status_code == 200
    response = requests.get(f"{p4.url}/api/account/export", headers=auth(token), timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["kitchens"][0]["items"] == ["rice", "toor-dal"] and data["kitchens"][0]["meals_per_day"] == 2
    assert data["meals"][0]["name"] == "Dal rice" and data["profiles"][0]["age"] == 30
    for secret in ("password_hash", "session_token", "code_hash", token):
        assert secret not in response.text, secret
    assert "user_id" not in data["kitchens"][0]
