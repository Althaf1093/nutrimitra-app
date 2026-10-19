"""Feature 1, item 2: plans built from the kitchen: the engine, the AI validation, the fallback and the shopping list."""
import json
import re
import uuid
from pathlib import Path

import pytest
import requests

import kitchen
import kitchen_plan as kp
import server
from conftest import p4_signup
from fakes import FakeProvider, openai_reply, spawn_backend, stop_backend

DISHES = Path(__file__).resolve().parents[1] / "data" / "dishes.json"
MEAT = {"chicken", "mutton", "fish", "prawns", "crab", "dried-fish"}
BIG_KITCHEN = [
    "rice", "wheat-flour", "ragi", "oats", "toor-dal", "moong-dal", "rajma", "chickpeas", "sprouts", "tomato", "onion", "potato", "brinjal", "okra", "cabbage",
    "carrot", "spinach", "gongura", "beans", "cauliflower", "drumstick", "green-peas", "curd", "milk", "buttermilk", "banana", "apple", "papaya",
    "peanuts", "almonds", "coconut", "jaggery", "egg", "paneer", "tofu", "soya-chunks", "chicken", "fish", "idli-batter", "poha", "semolina", "bread", "besan",
]


def profile(**extra):
    return {"age": 30, "sex": "Female", "height_cm": 160, "weight_kg": 60, "target_weight_kg": 58, "conditions": [], "dietary_preferences": ["Vegetarian"], "allergies": [], "disliked_foods": [],
            "activity_level": "Moderately active", "cooking_time": "20–30 min", "food_budget": "Balanced", "wellness_goal": "Healthier living", "language": "en", "timezone": "Asia/Kolkata", **extra}


def week(items, meals=3, time="20–30 min", **profile_fields):
    prof = profile(**profile_fields)
    ctx = kp.make_context(prof, {"items": items, "meals_per_day": meals, "household_size": 2, "cooking_time": time})
    return ctx, kp.build_week(ctx, prof, server.portion_for)


def all_meals(plan):
    return [meal for day in plan["days"] for meal in day["meals"]]


def used_ids(plan):
    return {iid for meal in all_meals(plan) for iid in meal["ingredients"]}


# ---- the dish file --------------------------------------------------------------------------------------------

def test_dishes_are_a_data_file_that_only_names_known_ingredients():
    data = json.loads(DISHES.read_text(encoding="utf-8"))["dishes"]
    assert len(data) >= 100
    groups = {item.group for item in kitchen.catalogue.items}
    names = [d["name"] for d in data]
    assert len(names) == len(set(names))
    for dish in data:
        assert dish["slots"] and set(dish["slots"]) <= set(kp.SLOT_ORDER) and dish["minutes"] > 0 and dish["cost"] in (1, 2, 3)
        for need in dish["needs"]:
            for alt in need["alts"]:
                assert alt[1:] in groups if alt.startswith("@") else alt in kitchen.catalogue.by_id, (dish["name"], alt)
        for iid in dish["uses"]:
            assert iid in kitchen.catalogue.by_id, (dish["name"], iid)
        bound = {n["var"] for n in dish["needs"] if n["var"]}
        assert set(re.findall(r"\{(\w+)\}", dish["name"] + dish["te"])) <= bound, dish["name"]
    for slot in kp.SLOT_ORDER:
        assert sum(slot in d["slots"] for d in data) >= 20, slot
    assert "Gongura" not in Path(server.__file__).read_text(encoding="utf-8")


# ---- the engine ------------------------------------------------------------------------------------------------

def test_a_week_has_seven_days_of_four_meals_from_the_kitchen():
    ctx, plan = week(BIG_KITCHEN)
    assert len(plan["days"]) == 7 and all([m["type"] for m in d["meals"]] == ["breakfast", "lunch", "snack", "dinner"] for d in plan["days"])
    assert plan["kitchen_based"] and plan["generated_by"] == "Wellstride kitchen engine" and plan["kitchen_hash"] == ctx.signature
    for meal in all_meals(plan):
        assert meal["ingredients"] or meal["name"] in {g[0] for g in kp.GENERIC.values()}
        for iid in meal["ingredients"]:
            assert iid in ctx.available or iid in meal["extras"], (meal["name"], iid)
        assert "{" not in meal["name"] and "{" not in meal["te"]
        assert meal["calories"] > 0 and meal["protein_g"] > 0
    assert len({m["name"] for m in all_meals(plan)}) >= 20, "varied, not the same few meals"


def test_the_engine_is_repeatable():
    assert week(BIG_KITCHEN)[1]["days"] == week(BIG_KITCHEN)[1]["days"]


@pytest.mark.parametrize("diet,banned", [
    (["Vegetarian"], MEAT | {"egg"}),
    (["Eggetarian"], MEAT),
    (["Vegan"], MEAT | {"egg", "paneer", "curd", "milk", "ghee", "butter", "buttermilk", "honey"}),
    (["Non-vegetarian", "Vegetarian"], MEAT | {"egg"}),
])
def test_the_engine_honours_the_diet(diet, banned):
    # The kitchen holds meat, fish, egg and dairy; the diet decides what the plan may touch.
    ctx, plan = week(BIG_KITCHEN, dietary_preferences=diet)
    assert not (used_ids(plan) & banned)
    names = " ".join(m["name"].lower() for m in all_meals(plan))
    for word in sorted(banned) + (["paneer"] if "paneer" in banned else []):
        assert re.search(rf"\b{re.escape(word.replace('-', ' '))}", names) is None, word


def test_a_non_vegetarian_plan_may_use_meat_and_egg():
    _, plan = week(BIG_KITCHEN, dietary_preferences=["Non-vegetarian"])
    assert used_ids(plan) & (MEAT | {"egg"})


def test_allergies_and_dislikes_are_never_used():
    ctx, plan = week(BIG_KITCHEN + ["peanut-butter", "groundnut-oil"], allergies=["peanut"], disliked_foods=["brinjal", "idli"])
    assert not (used_ids(plan) & {"peanuts", "peanut-butter", "groundnut-oil", "brinjal"})
    assert not re.search(r"peanut|brinjal|idli", " ".join(m["name"].lower() for m in all_meals(plan)))


def test_extras_stay_within_the_cap_and_match_the_also_buy_list():
    for items in (["rice"], ["rice", "toor-dal"], ["wheat-flour", "potato", "onion"], ["ragi"], BIG_KITCHEN[:12]):
        ctx, plan = week(items)
        extras = kp.plan_extras(plan["days"])
        assert len(extras) <= kp.MAX_EXTRAS and plan["also_buy"] == extras
        assert not (set(extras) & ctx.kitchen_ids)
        for meal in all_meals(plan):
            assert len(meal["extras"]) <= 1
        assert len(all_meals(plan)) == 28, "even a tiny kitchen gets a full week"


def test_a_full_kitchen_needs_nothing_extra():
    assert week(BIG_KITCHEN)[1]["also_buy"] == []


def test_cooking_time_limits_the_dishes():
    ctx, quick = week(BIG_KITCHEN, time="Under 15 min")
    dishes_by_name = {d.name: d for d in kp.dishes()}
    for meal in all_meals(quick):
        assert meal["minutes"] <= 15, meal["name"]
    _, enjoy = week(BIG_KITCHEN, time="I enjoy cooking")
    assert max(m["minutes"] for m in all_meals(enjoy)) > 30, "someone who enjoys cooking gets longer dishes too"
    assert dishes_by_name


def test_meals_not_cooked_at_home_need_no_real_cooking():
    ctx, plan = week(BIG_KITCHEN, meals=1)
    assert ctx.cooked == {"lunch"}
    for meal in all_meals(plan):
        if meal["type"] in ("breakfast", "dinner", "snack"):
            assert meal["minutes"] <= kp.SNACK_MINUTES, (meal["type"], meal["name"])
        if meal["type"] in ("breakfast", "dinner"):
            assert meal["minutes"] <= kp.NO_COOK_MINUTES, (meal["type"], meal["name"])


def test_budget_friendly_skips_expensive_dishes():
    _, plan = week(BIG_KITCHEN + ["prawns", "mutton"], dietary_preferences=["Non-vegetarian"], food_budget="Budget-friendly")
    costly = {d.name for d in kp.dishes() if d.cost == 3}
    assert not (used_ids(plan) & {"prawns", "mutton"})
    assert not ({m["name"] for m in all_meals(plan)} & costly)


def test_the_kitchen_signature_follows_what_shapes_the_plan():
    base = {"items": ["rice", "ragi"], "meals_per_day": 3, "cooking_time": "Under 15 min"}
    assert kp.kitchen_signature(base) == kp.kitchen_signature({**base, "items": ["ragi", "rice"], "household_size": 9})
    assert kp.kitchen_signature(base) != kp.kitchen_signature({**base, "items": ["rice"]})
    assert kp.kitchen_signature(base) != kp.kitchen_signature({**base, "meals_per_day": 2})
    assert kp.kitchen_signature({"items": []}) is None and kp.kitchen_signature(None) is None


# ---- the server: AI plans are checked, the engine answers when they are not ----------------------------------------

@pytest.fixture(scope="module")
def stack():
    fake = FakeProvider()
    url, proc = spawn_backend({"GROQ_API_KEY": "test-groq-key", "GROQ_BASE_URL": fake.url, "AUTH_RATE_LIMIT_EXEMPT_IPS": "127.0.0.1,::1", "GOOGLE_CLIENT_IDS": ""})
    yield fake, url
    stop_backend(proc)
    fake.close()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def person(url, items, **profile_fields):
    email = f"kplan.{uuid.uuid4().hex[:10]}@example.com"
    response = requests.post(f"{url}/api/auth/signup", json={"email": email, "password": "StrongPass123", "name": "Kitchen", "accept_terms": True}, timeout=20)
    token = response.json()["token"]
    assert requests.put(f"{url}/api/profile", json=profile(**profile_fields), headers=auth(token), timeout=20).status_code == 200
    if items is not None:
        saved = requests.put(f"{url}/api/kitchen", json={"items": items, "meals_per_day": 3, "household_size": 3, "cooking_time": "20–30 min"}, headers=auth(token), timeout=20)
        assert saved.status_code == 200, saved.text
    return token


def ai_plan(meal_ingredients):
    """A scripted AI plan: the same ingredient names for every meal (the names the model would copy from the lists)."""
    days = []
    for number in range(1, 8):
        meals = [{"type": slot, "name": f"{slot.title()} {number}", "portion": "1 bowl", "calories": 400, "protein_g": 20, "carbs_g": 50, "fat_g": 12, "ingredients": list(meal_ingredients)}
                 for slot in ("breakfast", "lunch", "snack", "dinner")]
        days.append({"day": number, "title": f"Day {number}", "focus": "Balanced", "meals": meals})
    return json.dumps({"days": days, "reasoning": "From your kitchen."})


def get_plan(url, token):
    response = requests.get(f"{url}/api/plan", headers=auth(token), timeout=60)
    assert response.status_code == 200, response.text
    return response.json()


def regenerate(url, token):
    response = requests.post(f"{url}/api/plan/regenerate", json={}, headers=auth(token), timeout=60)
    assert response.status_code == 200, response.text
    return response.json()


def plan_ingredient_ids(plan):
    return {i for day in plan["days"] for meal in day["meals"] for i in meal["ingredients"]}


def test_a_valid_ai_plan_is_used_and_carries_ingredients(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "tomato", "onion", "curd", "banana"])
    fake.reset()
    fake.queue(200, openai_reply(ai_plan(["Rice", "Toor dal (arhar)", "Tomato", "Curd (yogurt)", "Salt", "Turmeric"])))
    plan = get_plan(url, token)
    assert plan["generated_by"] == "groq kitchen engine" and plan["kitchen_based"] is True
    assert plan_ingredient_ids(plan) == {"rice", "toor-dal", "tomato", "curd"}, "pantry basics are not listed, names become ids"
    assert plan["also_buy"] == []
    meal = plan["days"][0]["meals"][0]
    assert {u["id"] for u in meal["uses"]} == {"rice", "toor-dal", "tomato", "curd"} and all(u["have"] for u in meal["uses"]) and meal["uses"][0]["name"]
    # The model was told about the kitchen, the extras it may add and the cap.
    sent = fake.requests[0]["body"]["messages"]
    assert "planning engine" in sent[0]["content"] and "max_extra_items" in sent[0]["content"]
    context = json.loads(sent[1]["content"].split("Context: ", 1)[1])
    assert "Toor dal (arhar)" in context["kitchen_items"] and context["max_extra_items"] == kp.MAX_EXTRAS and "Chicken" not in context["extra_items_allowed"]


def test_a_few_extras_are_allowed_and_listed_as_also_buy(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "tomato"])
    fake.reset()
    fake.queue(200, openai_reply(ai_plan(["Rice", "Toor dal (arhar)", "Spinach", "Paneer"])))
    plan = get_plan(url, token)
    assert plan["generated_by"] == "groq kitchen engine"
    assert {item["id"] for item in plan["also_buy"]} == {"spinach", "paneer"}
    assert all(not u["have"] for u in plan["days"][0]["meals"][0]["uses"] if u["id"] in {"spinach", "paneer"})


@pytest.mark.parametrize("name,ingredients", [
    ("meat for a vegetarian", ["Rice", "Chicken"]),
    ("too many extras", ["Rice", "Spinach", "Paneer", "Tofu", "Cauliflower", "Carrot", "Beetroot"]),
    ("an ingredient that does not exist", ["Rice", "Unobtainium"]),
    ("no ingredient list", None),
])
def test_an_ai_plan_that_does_not_fit_is_replaced_by_the_kitchen_engine(stack, name, ingredients):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "tomato", "onion", "curd", "potato", "banana", "wheat-flour"], dietary_preferences=["Vegetarian"])
    fake.reset()
    body = json.loads(ai_plan(["x"]))
    for day in body["days"]:
        for meal in day["meals"]:
            if ingredients is None:
                meal.pop("ingredients")
            else:
                meal["ingredients"] = ingredients
    fake.queue(200, openai_reply(json.dumps(body)))
    plan = get_plan(url, token)
    assert plan["generated_by"] == "Wellstride kitchen engine", name
    assert not (plan_ingredient_ids(plan) & MEAT)
    assert len(plan["also_buy"]) <= kp.MAX_EXTRAS


def test_a_vegetarian_plan_by_the_ai_with_a_meat_dish_name_is_rejected_too(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "tomato"], dietary_preferences=["Vegetarian"])
    fake.reset()
    body = json.loads(ai_plan(["Rice", "Toor dal (arhar)"]))
    body["days"][2]["meals"][1]["name"] = "Chicken biryani"
    fake.queue(200, openai_reply(json.dumps(body)))
    assert get_plan(url, token)["generated_by"] == "Wellstride kitchen engine"


def test_when_the_ai_is_busy_the_kitchen_engine_answers(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "tomato", "onion", "potato", "wheat-flour", "curd"])
    fake.reset()
    for _ in range(4):
        fake.queue(429, {"error": {"message": "Rate limit"}}, {"Retry-After": "0"})
    plan = regenerate(url, token)
    assert plan["generated_by"] == "Wellstride kitchen engine" and plan["kitchen_based"] is True
    assert plan["updated_at"], "the plan is dated, so it is the newest one and Day 1 has a date"
    assert len(plan["days"]) == 7 and all(len(d["meals"]) == 4 for d in plan["days"])


def test_when_the_ai_returns_nonsense_the_kitchen_engine_answers(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal"])
    fake.reset()
    fake.queue(200, openai_reply("sorry, I cannot do that"))
    assert get_plan(url, token)["generated_by"] == "Wellstride kitchen engine"


def test_without_a_kitchen_plans_are_as_before(stack):
    fake, url = stack
    token = person(url, None)
    fake.reset()
    fake.queue(200, openai_reply(ai_plan(["Whatever"])))
    plan = get_plan(url, token)
    assert plan["kitchen_based"] is False and plan["generated_by"] == "groq adaptive engine" and plan["also_buy"] == []
    system = fake.requests[0]["body"]["messages"][0]["content"]
    assert "kitchen_items" not in system
    assert plan["kitchen_changed"] is False


def test_the_plan_says_when_the_kitchen_changed(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "tomato", "onion"])
    fake.reset()
    fake.queue(200, openai_reply("not json"))
    assert get_plan(url, token)["kitchen_changed"] is False
    assert requests.put(f"{url}/api/kitchen", json={"items": ["rice", "toor-dal", "tomato", "onion", "potato"], "meals_per_day": 3, "household_size": 3, "cooking_time": "20–30 min"}, headers=auth(token), timeout=20).status_code == 200
    assert get_plan(url, token)["kitchen_changed"] is True
    # household size does not shape the plan, so it does not count as a change
    fake.queue(200, openai_reply("not json"))
    assert regenerate(url, token)["kitchen_changed"] is False
    assert requests.put(f"{url}/api/kitchen", json={"items": ["rice", "toor-dal", "tomato", "onion", "potato"], "meals_per_day": 3, "household_size": 5, "cooking_time": "20–30 min"}, headers=auth(token), timeout=20).status_code == 200
    assert get_plan(url, token)["kitchen_changed"] is False


def test_the_shopping_list_is_the_plan_minus_the_kitchen(stack):
    fake, url = stack
    items = ["rice", "toor-dal", "tomato"]
    token = person(url, items)
    fake.reset()
    fake.queue(200, openai_reply(ai_plan(["Rice", "Toor dal (arhar)", "Tomato", "Paneer", "Spinach"])))
    get_plan(url, token)
    listing = requests.get(f"{url}/api/plan/shopping-list", headers=auth(token), timeout=20).json()
    assert listing["kitchen_based"] is True and listing["household_size"] == 3
    assert {row["id"] for row in listing["to_buy"]} == {"paneer", "spinach"}
    assert {row["id"] for row in listing["have"]} == set(items)
    assert all(row["meals"] == 28 and row["name"] and row["te"] for row in listing["to_buy"] + listing["have"])
    assert [row["group"] for row in listing["to_buy"]] == ["leafy", "protein"], "grouped in the order of the shop aisles"
    assert listing["kitchen_changed"] is False
    # Having bought spinach and added it to the kitchen, it leaves the list.
    requests.put(f"{url}/api/kitchen", json={"items": items + ["spinach"], "meals_per_day": 3, "household_size": 3, "cooking_time": "20–30 min"}, headers=auth(token), timeout=20)
    listing = requests.get(f"{url}/api/plan/shopping-list", headers=auth(token), timeout=20).json()
    assert {row["id"] for row in listing["to_buy"]} == {"paneer"} and "spinach" in {row["id"] for row in listing["have"]}


def test_the_shopping_list_of_a_plan_without_a_kitchen_is_empty(stack):
    fake, url = stack
    token = person(url, None)
    fake.reset()
    fake.queue(200, openai_reply(ai_plan(["x"])))
    get_plan(url, token)
    listing = requests.get(f"{url}/api/plan/shopping-list", headers=auth(token), timeout=20).json()
    assert listing["kitchen_based"] is False and listing["to_buy"] == [] and listing["have"] == []


def test_shopping_list_needs_sign_in(stack):
    _, url = stack
    assert requests.get(f"{url}/api/plan/shopping-list", timeout=20).status_code == 401


def test_a_vegetarian_kitchen_plan_from_a_mixed_kitchen_never_has_meat_end_to_end(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "paneer", "curd", "onion", "tomato", "potato", "wheat-flour", "banana", "okra"], dietary_preferences=["Vegetarian"])
    fake.reset()
    fake.queue(200, openai_reply("nonsense"))
    plan = get_plan(url, token)
    text = json.dumps(plan).lower()
    for word in ("chicken", "mutton", "prawn", "fish curry", "egg "):
        assert word not in text, word
    assert plan["generated_by"] == "Wellstride kitchen engine" and len(plan_ingredient_ids(plan)) >= 6


def test_a_dish_name_never_mentions_an_ingredient_the_dish_does_not_need():
    """Otherwise a vegan could be shown "...with curd" because curd was only an optional extra."""
    import foods

    problems = []
    for dish in kp.dishes():
        needed = {alt for need in dish.needs for alt in need.alts if not alt.startswith("@")}
        needed_words = {w for iid in needed for w in foods.normalize(kitchen.catalogue.by_id[iid].name).split()}
        words = set(foods.normalize(re.sub(r"\{\w+\}", "", dish.name)).split())
        for item in kitchen.catalogue.items:
            if item.assumed or item.group == "pantry" or item.id in needed:
                continue
            main = {w for w in foods.normalize(item.name.split("(")[0]).split() if len(w) > 2}
            if main and main <= words and not main <= needed_words:
                problems.append((dish.name, item.id))
    assert problems == []
