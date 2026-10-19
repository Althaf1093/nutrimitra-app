"""UX run item 2: the food catalogue and GET /api/foods/search, /recent and /frequent."""
import json
from pathlib import Path

import pytest
import requests

import foods
from conftest import p4_signup
from fakes import spawn_backend, stop_backend

DATA = Path(__file__).resolve().parents[1] / "data" / "foods.json"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def new_user(p4):
    response, _ = p4_signup(p4)
    return response.json()["token"]


def search(p4, token, q, **params):
    response = requests.get(f"{p4.url}/api/foods/search", params={"q": q, **params}, headers=auth(token), timeout=20)
    assert response.status_code == 200, response.text
    return response.json()


def names(payload):
    return [item["name"] for item in payload["results"]]


def log(p4, token, name, **extra):
    body = {"meal_type": "snack", "name": name, "calories": 100, "protein_g": 5, "carbs_g": 10, "fat_g": 3, "source": "manual", **extra}
    response = requests.post(f"{p4.url}/api/meals", json=body, headers=auth(token), timeout=20)
    assert response.status_code == 200, response.text
    return response.json()


# ---- the data file -------------------------------------------------------------------------------------------

def test_catalogue_is_a_data_file_with_enough_complete_foods():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = data["foods"]
    assert len(items) >= 400
    assert "estimate" in data["note"].lower()
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids)), "food ids are unique"
    for item in items:
        assert item["name"] and item["category"] and item["serving"], item["id"]
        for key in ("calories", "protein_g", "carbs_g", "fat_g"):
            assert isinstance(item[key], (int, float)) and item[key] >= 0, (item["id"], key)
        assert item["calories"] <= 1500, item["id"]
        for option in item["servings"]:
            assert option["label"] and option["factor"] > 0, item["id"]
    assert sum(1 for item in items if item.get("te")) >= 350, "most foods have a Telugu name"
    categories = {item["category"] for item in items}
    for needed in ("Eggs", "Tiffin", "Rice & mains", "Dal & sambar", "Chicken", "Fish & seafood", "Dairy & paneer", "Snacks", "Sweets", "Drinks", "Fruits", "Millets & grains"):
        assert needed in categories


def test_server_does_not_hardcode_the_catalogue():
    source = (Path(__file__).resolve().parents[1] / "server.py").read_text(encoding="utf-8")
    assert "Boiled egg" not in source and "Masala dosa" not in source


# ---- search ---------------------------------------------------------------------------------------------------

def test_egg_surfaces_the_whole_egg_family(p4):
    token = new_user(p4)
    found = names(search(p4, token, "egg"))
    for expected in ("Boiled egg", "Omelette", "Scrambled egg", "Fried egg (half-fry)", "Egg curry", "Egg bhurji", "Egg white"):
        assert expected in found, expected
    assert names(search(p4, token, "EGGS"))[:3] == found[:3], "case and plurals are forgiven"


def test_search_rows_carry_what_the_app_needs(p4):
    token = new_user(p4)
    payload = search(p4, token, "egg")
    assert payload["kind"] == "search" and "estimate" in payload["note"].lower()
    row = payload["results"][0]
    for key in ("id", "name", "te", "category", "serving", "calories", "protein_g", "carbs_g", "fat_g", "servings", "estimate", "recent"):
        assert key in row, key
    assert row["estimate"] is True
    assert row["servings"][0] == {"label": row["serving"], "factor": 1.0}, "the default serving is the first option"


def test_dosa_gives_many_variants(p4):
    token = new_user(p4)
    found = names(search(p4, token, "dosa", limit=50))
    dosas = [name for name in found if "dosa" in name.lower() or name == "Pesarattu"]
    assert len(dosas) >= 8
    for expected in ("Plain dosa", "Masala dosa", "Ragi dosa", "Karam dosa", "Rava dosa", "Pesarattu", "Set dosa", "Onion dosa"):
        assert expected in found, expected


def test_idli_variants(p4):
    token = new_user(p4)
    found = names(search(p4, token, "idli", limit=30))
    for expected in ("Idli", "Ragi idli", "Rava idli", "Mini idli", "Podi idli"):
        assert expected in found, expected


@pytest.mark.parametrize("typo,expected", [("dosaa", "Plain dosa"), ("dossa", "Masala dosa"), ("omlet", "Omelette"), ("idlli", "Idli"), ("chiken curry", "Chicken curry"), ("panner", "Paneer butter masala")])
def test_typos_are_forgiven(p4, typo, expected):
    token = new_user(p4)
    assert expected in names(search(p4, token, typo, limit=30))


def test_synonyms_and_partial_words(p4):
    token = new_user(p4)
    assert "Tea with milk and sugar" in names(search(p4, token, "chai"))
    assert "Masala dosa" in names(search(p4, token, "masala dos"))
    assert "Phulka (no oil)" in names(search(p4, token, "phulka"))


def test_telugu_queries(p4):
    token = new_user(p4)
    assert "Plain dosa" in names(search(p4, token, "దోశ", limit=30))
    assert "Boiled egg" in names(search(p4, token, "గుడ్డు", limit=30))
    assert "Idli" in names(search(p4, token, "ఇడ్లీ", limit=30))


def test_no_match_is_an_empty_list_not_an_error(p4):
    token = new_user(p4)
    payload = search(p4, token, "zzzxqvw")
    assert payload["results"] == [] and payload["kind"] == "search"


def test_limit_is_respected_and_validated(p4):
    token = new_user(p4)
    assert len(search(p4, token, "rice", limit=3)["results"]) == 3
    assert requests.get(f"{p4.url}/api/foods/search", params={"q": "rice", "limit": 0}, headers=auth(token), timeout=20).status_code == 422
    assert requests.get(f"{p4.url}/api/foods/search", params={"q": "rice", "limit": 500}, headers=auth(token), timeout=20).status_code == 422


def test_recently_logged_foods_rank_higher(p4):
    token = new_user(p4)
    before = names(search(p4, token, "egg", limit=30))
    assert before.index("Egg white") > 3
    log(p4, token, "Egg white")
    after = search(p4, token, "egg", limit=30)
    assert names(after).index("Egg white") <= 1
    assert next(item for item in after["results"] if item["name"] == "Egg white")["recent"] is True
    assert next(item for item in after["results"] if item["name"] == "Boiled egg")["recent"] is False


def test_empty_query_returns_recents_or_common_foods(p4):
    token = new_user(p4)
    fresh = search(p4, token, "")
    assert fresh["kind"] == "popular" and len(fresh["results"]) > 5
    assert search(p4, token, "   ")["kind"] == "popular"
    log(p4, token, "Masala dosa")
    log(p4, token, "Boiled egg")
    recent = search(p4, token, "")
    assert recent["kind"] == "recent"
    assert names(recent)[:2] == ["Boiled egg", "Masala dosa"], "newest first"
    assert all(item["recent"] for item in recent["results"])


# ---- recent and frequent --------------------------------------------------------------------------------------

def test_recent_foods_are_distinct_newest_first_and_include_custom_ones(p4):
    token = new_user(p4)
    log(p4, token, "Idli")
    log(p4, token, "My aunt's thali", calories=640, protein_g=22, carbs_g=80, fat_g=24, portion="1 plate")
    log(p4, token, "idli")  # the same food again, other letter case
    response = requests.get(f"{p4.url}/api/foods/recent", headers=auth(token), timeout=20)
    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["name"] for item in results] == ["Idli", "My aunt's thali"]
    custom = results[1]
    assert custom["category"] == "Logged" and custom["calories"] == 640 and custom["serving"] == "1 plate" and custom["estimate"] is False


def test_frequent_foods_need_two_logs(p4):
    token = new_user(p4)
    log(p4, token, "Upma")
    log(p4, token, "Poha")
    log(p4, token, "Poha")
    results = requests.get(f"{p4.url}/api/foods/frequent", headers=auth(token), timeout=20).json()["results"]
    assert [item["name"] for item in results] == ["Poha"]
    assert results[0]["times"] == 2


def test_each_person_sees_only_their_own_recents(p4):
    one, two = new_user(p4), new_user(p4)
    log(p4, one, "Pongal")
    assert requests.get(f"{p4.url}/api/foods/recent", headers=auth(two), timeout=20).json()["results"] == []


# ---- the meal log keeps the serving ----------------------------------------------------------------------------

def test_a_logged_meal_keeps_its_serving_text(p4):
    token = new_user(p4)
    meal = log(p4, token, "Boiled egg", portion="2 eggs")
    assert meal["portion"] == "2 eggs"
    dashboard = requests.get(f"{p4.url}/api/dashboard", headers=auth(token), timeout=20).json()
    assert dashboard["meals"][0]["portion"] == "2 eggs"
    plain = log(p4, token, "Boiled egg")
    assert "portion" not in plain, "meals logged without a serving look exactly as before"
    response = requests.post(f"{p4.url}/api/meals", json={"meal_type": "snack", "name": "x", "calories": 1, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "portion": "y" * 200}, headers=auth(token), timeout=20)
    assert response.status_code == 422


# ---- access and limits ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/foods/search?q=egg", "/foods/search", "/foods/recent", "/foods/frequent"])
def test_food_endpoints_need_sign_in(p4, path):
    assert requests.get(f"{p4.url}/api{path}", timeout=20).status_code == 401
    assert requests.get(f"{p4.url}/api{path}", headers=auth("not-a-token"), timeout=20).status_code == 401


def test_searches_are_rate_limited_per_person():
    url, proc = spawn_backend({"FOODS_RATE_LIMIT": "5"})
    try:
        def signup():
            email = f"foodlimit.{__import__('uuid').uuid4().hex[:10]}@example.com"
            body = {"email": email, "password": "StrongPass123", "name": "Limit", "accept_terms": True}
            return requests.post(f"{url}/api/auth/signup", json=body, timeout=20).json()["token"]

        busy, other = signup(), signup()
        codes = [requests.get(f"{url}/api/foods/search", params={"q": "egg"}, headers=auth(busy), timeout=20).status_code for _ in range(7)]
        assert codes == [200] * 5 + [429] * 2
        limited = requests.get(f"{url}/api/foods/search", params={"q": "egg"}, headers=auth(busy), timeout=20)
        assert int(limited.headers["Retry-After"]) >= 1
        assert requests.get(f"{url}/api/foods/search", params={"q": "egg"}, headers=auth(other), timeout=20).status_code == 200
    finally:
        stop_backend(proc)


# ---- the search code itself -----------------------------------------------------------------------------------

def test_normalize_keeps_telugu_vowel_signs_and_drops_punctuation():
    assert foods.normalize("Fried egg (half-fry)!") == "fried egg half fry"
    assert foods.normalize("దోశ") == "దోశ"
    assert foods.normalize("  Masala   DOSA ") == "masala dosa"


def test_edit_distance_counts_typos_and_swaps():
    assert foods.edit_distance("dosa", "dosa", 2) == 0
    assert foods.edit_distance("dosaa", "dosa", 2) == 1
    assert foods.edit_distance("idil", "idli", 2) == 1, "an adjacent swap is one typo"
    assert foods.edit_distance("abc", "xyzxyz", 1) > 1


def test_search_without_the_server_ranks_family_before_look_alikes():
    found = [item["name"] for item in foods.catalogue.search("dosa", 40)]
    assert found.index("Plain dosa") < found.index("Dosakaya pappu")
    assert "Cucumber slices" not in found[:25]


@pytest.mark.parametrize("word,category", [("snacks", "Snacks"), ("fruits", "Fruits"), ("drinks", "Drinks"), ("sweets", "Sweets"), ("egg", "Eggs")])
def test_a_category_word_browses_the_category(p4, word, category):
    token = new_user(p4)
    top = search(p4, token, word, limit=10)["results"]
    assert len(top) == 10
    assert sum(1 for item in top if item["category"] == category) >= 8, [item["name"] for item in top]
