"""Feature 1, item 3: the daily loop: swap a meal, "I ate something else", and the evening check-in that adapts tomorrow."""
import json

import pytest
import requests

import kitchen
import kitchen_plan as kp
from fakes import openai_reply
from test_kitchen_plan import MEAT, auth, get_plan, person, stack  # noqa: F401  (stack is a fixture)

KITCHEN = ["rice", "wheat-flour", "toor-dal", "moong-dal", "tomato", "onion", "potato", "brinjal", "okra", "spinach", "curd", "milk", "paneer", "banana", "apple", "peanuts", "idli-batter", "oats", "bread", "besan", "sprouts", "chickpeas", "soya-chunks", "tofu"]


def kitchen_person(url, fake, diet=("Vegetarian",)):
    token = person(url, KITCHEN, dietary_preferences=list(diet))
    fake.reset()
    fake.queue(200, openai_reply("not json"))  # the kitchen engine makes the plan
    get_plan(url, token)
    return token


def swap_options(url, token, day=0, slot="lunch"):
    return requests.get(f"{url}/api/plan/swap", params={"day": day, "type": slot}, headers=auth(token), timeout=20)


def swap(url, token, day, slot, name):
    return requests.post(f"{url}/api/plan/swap", json={"day": day, "type": slot, "name": name}, headers=auth(token), timeout=20)


def planned(plan):
    """What is planned, day by day (not the logged flags, which change as the person eats)."""
    return [[(m["type"], m["name"]) for m in d["meals"]] for d in plan["days"]]


def meal_of(plan, day, slot):
    return next(m for m in plan["days"][day]["meals"] if m["type"] == slot)


def log(url, token, name, meal_type="lunch", calories=400, protein=15, **extra):
    body = {"meal_type": meal_type, "name": name, "calories": calories, "protein_g": protein, "carbs_g": 50, "fat_g": 10, "source": "manual", **extra}
    response = requests.post(f"{url}/api/meals", json=body, headers=auth(token), timeout=20)
    assert response.status_code == 200, response.text
    return response.json()


# ---- swap ------------------------------------------------------------------------------------------------------

def test_swap_offers_three_other_meals_from_the_same_kitchen(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    plan = get_plan(url, token)
    current = meal_of(plan, 0, "lunch")["name"]
    response = swap_options(url, token)
    assert response.status_code == 200, response.text
    options = response.json()["alternatives"]
    assert len(options) == 3 and len({o["name"] for o in options}) == 3
    for option in options:
        assert option["type"] == "lunch" and option["name"] != current
        assert option["calories"] > 0 and option["uses"], option["name"]
        assert not ({u["id"] for u in option["uses"]} & MEAT)
        assert all(u["have"] or len([x for x in option["uses"] if not x["have"]]) <= 1 for u in option["uses"])


def test_swap_replaces_only_that_meal(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    before = get_plan(url, token)
    chosen = swap_options(url, token, day=2, slot="dinner").json()["alternatives"][1]
    response = swap(url, token, 2, "dinner", chosen["name"])
    assert response.status_code == 200, response.text
    after = response.json()
    assert meal_of(after, 2, "dinner")["name"] == chosen["name"] and meal_of(after, 2, "dinner")["type"] == "dinner"
    assert [m["name"] for d in after["days"] for m in d["meals"] if not (d["day"] == 3 and m["type"] == "dinner")] == [m["name"] for d in before["days"] for m in d["meals"] if not (d["day"] == 3 and m["type"] == "dinner")]
    assert get_plan(url, token)["days"][2]["meals"][3]["name"] == chosen["name"], "kept, not just returned"
    assert len(after["also_buy"]) <= kp.MAX_EXTRAS
    assert not ({u["id"] for d in after["days"] for m in d["meals"] for u in m["uses"]} & MEAT)


def test_swap_only_accepts_a_real_option(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    assert swap(url, token, 0, "lunch", "Chicken biryani").status_code == 422
    assert swap(url, token, 0, "lunch", "Made up meal").status_code == 422
    assert swap(url, token, 0, "elevenses", "Tea").status_code == 422
    assert swap_options(url, token, slot="elevenses").status_code == 422
    assert requests.get(f"{url}/api/plan/swap", params={"day": 9, "type": "lunch"}, headers=auth(token), timeout=20).status_code == 422
    assert swap(url, token, 9, "lunch", "x").status_code == 422


def test_a_meal_already_logged_cannot_be_swapped(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    plan = get_plan(url, token)
    today = plan["today_index"]
    lunch = meal_of(plan, today, "lunch")
    log(url, token, lunch["name"], "lunch", source="plan")
    chosen = swap_options(url, token, day=today, slot="lunch").json()["alternatives"][0]
    response = swap(url, token, today, "lunch", chosen["name"])
    assert response.status_code == 409
    # tomorrow's lunch is still free to swap
    nxt = (today + 1) % 7
    other = swap_options(url, token, day=nxt, slot="lunch").json()["alternatives"][0]
    assert swap(url, token, nxt, "lunch", other["name"]).status_code == 200


def test_swap_needs_a_plan_and_a_sign_in(stack):
    fake, url = stack
    token = person(url, KITCHEN)
    assert swap_options(url, token).status_code == 404, "no plan has been made yet"
    assert swap(url, token, 0, "lunch", "x").status_code == 404
    assert requests.get(f"{url}/api/plan/swap", params={"day": 0, "type": "lunch"}, timeout=20).status_code == 401
    assert requests.post(f"{url}/api/plan/swap", json={"day": 0, "type": "lunch", "name": "x"}, timeout=20).status_code == 401


def test_one_persons_swap_does_not_touch_another_persons_plan(stack):
    fake, url = stack
    one, two = kitchen_person(url, fake), kitchen_person(url, fake)
    before = get_plan(url, two)
    chosen = swap_options(url, one, day=1, slot="breakfast").json()["alternatives"][0]
    assert swap(url, one, 1, "breakfast", chosen["name"]).status_code == 200
    assert planned(get_plan(url, two)) == planned(before)


def test_swap_works_without_a_kitchen_too(stack):
    fake, url = stack
    token = person(url, None, dietary_preferences=["Vegetarian"])
    fake.reset()
    fake.queue(200, openai_reply("nonsense"))
    get_plan(url, token)
    options = swap_options(url, token, slot="dinner").json()["alternatives"]
    assert len(options) == 3 and not (MEAT & {u["id"] for o in options for u in o["uses"]})
    assert all(u["have"] for o in options for u in o["uses"]), "no kitchen to be missing things from"
    chosen = options[0]["name"]
    after = swap(url, token, 0, "dinner", chosen).json()
    assert meal_of(after, 0, "dinner")["name"] == chosen and after["kitchen_based"] is False and after["also_buy"] == []


def test_swap_respects_allergies_and_a_small_kitchen(stack):
    fake, url = stack
    token = person(url, ["rice", "toor-dal", "wheat-flour", "potato", "onion", "tomato"], dietary_preferences=["Vegetarian"], allergies=["peanut"])
    fake.reset()
    fake.queue(200, openai_reply("nonsense"))
    get_plan(url, token)
    for slot in ("breakfast", "lunch", "snack", "dinner"):
        for option in swap_options(url, token, day=3, slot=slot).json()["alternatives"]:
            assert "peanut" not in option["name"].lower() and "peanuts" not in {u["id"] for u in option["uses"]}


# ---- "I ate something else" -------------------------------------------------------------------------------------

def test_a_meal_logged_in_the_slot_marks_the_planned_one_as_replaced(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    plan = get_plan(url, token)
    today = plan["today_index"]
    assert not any(m["logged"] or m["ate_other"] for m in plan["days"][today]["meals"])
    log(url, token, "Something from the canteen", "lunch")
    after = get_plan(url, token)
    lunch = meal_of(after, today, "lunch")
    assert lunch["ate_other"] is True and lunch["logged"] is False
    assert not meal_of(after, today, "dinner")["ate_other"]
    assert not any(m["ate_other"] for i, d in enumerate(after["days"]) if i != today for m in d["meals"]), "only today"
    # Logging the planned meal itself counts as logged, not as something else.
    token2 = kitchen_person(url, fake)
    plan2 = get_plan(url, token2)
    planned = meal_of(plan2, plan2["today_index"], "breakfast")
    log(url, token2, planned["name"], "breakfast", source="plan")
    meal = meal_of(get_plan(url, token2), plan2["today_index"], "breakfast")
    assert meal["logged"] is True and meal["ate_other"] is False


# ---- the evening check-in ------------------------------------------------------------------------------------------

def checkin(url, token):
    response = requests.post(f"{url}/api/checkin", headers=auth(token), timeout=30)
    assert response.status_code == 200, response.text
    return response.json()


def targets(url, token):
    calories = requests.get(f"{url}/api/dashboard", headers=auth(token), timeout=20).json()["target_calories"]
    return calories, round(calories * 0.20 / 4)


def protein_dishes(day):
    return sum(any(kitchen.catalogue.by_id[i].protein for i in meal["ingredients"]) for meal in day["meals"] if meal["type"] != "snack")


def test_nothing_logged_means_no_check_in_and_no_change(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    before = get_plan(url, token)
    result = checkin(url, token)["result"]
    assert result["status"] == "nothing_logged" and result["adjusted_day"] is None
    assert planned(get_plan(url, token)) == planned(before)
    assert requests.get(f"{url}/api/checkin", headers=auth(token), timeout=20).json()["result"]["status"] == "nothing_logged"


def test_low_protein_makes_tomorrow_lean_on_protein_from_the_kitchen(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    before = get_plan(url, token)
    today = before["today_index"]
    tomorrow = (today + 1) % 7
    calories, protein = targets(url, token)
    log(url, token, "Plain rice and ghee", "lunch", calories=int(calories * 0.8), protein=round(protein * 0.3))
    response = checkin(url, token)
    result = response["result"]
    assert response["repeat"] is False and result["status"] == "low_protein" and result["adjusted_day"] == tomorrow
    assert result["protein_g"] < result["target_protein_g"] * 0.75 and result["target_protein_g"] == protein

    after = get_plan(url, token)
    assert after["days"][tomorrow]["focus"] == "Protein-forward day"
    assert protein_dishes(after["days"][tomorrow]) >= protein_dishes(before["days"][tomorrow])
    for slot in ("lunch", "dinner"):
        assert any(kitchen.catalogue.by_id[i].protein for i in meal_of(after, tomorrow, slot)["ingredients"]), f"{slot} leans on a protein-rich kitchen item"
    for i, day in enumerate(after["days"]):
        if i != tomorrow:
            assert [m["name"] for m in day["meals"]] == [m["name"] for m in before["days"][i]["meals"]], "only tomorrow changes"
    assert not ({u["id"] for m in after["days"][tomorrow]["meals"] for u in m["uses"]} & MEAT), "still vegetarian"
    assert len(after["also_buy"]) <= kp.MAX_EXTRAS


def test_a_balanced_day_changes_nothing(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    before = get_plan(url, token)
    calories, protein = targets(url, token)
    log(url, token, "A good lunch", "lunch", calories=calories, protein=protein + 5)
    result = checkin(url, token)["result"]
    assert result["status"] == "on_track" and result["adjusted_day"] is None
    assert planned(get_plan(url, token)) == planned(before)


@pytest.mark.parametrize("calorie_factor,expected", [(0.3, "low_energy"), (1.4, "above")])
def test_low_or_high_energy_is_reported_without_changing_the_plan(stack, calorie_factor, expected):
    fake, url = stack
    token = kitchen_person(url, fake)
    before = get_plan(url, token)
    calories, protein = targets(url, token)
    total = int(calories * calorie_factor)
    log(url, token, "Meal one", "lunch", calories=min(total, 2500), protein=protein)
    if total > 2500:
        log(url, token, "Meal two", "dinner", calories=total - 2500, protein=0)
    result = checkin(url, token)["result"]
    assert result["status"] == expected and result["adjusted_day"] is None
    assert planned(get_plan(url, token)) == planned(before)


def test_a_second_check_in_the_same_day_gives_the_same_answer_and_does_not_rebuild(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    calories, protein = targets(url, token)
    log(url, token, "Low protein meal", "lunch", calories=calories // 2, protein=2)
    first = checkin(url, token)
    plan_after_first = get_plan(url, token)
    second = checkin(url, token)
    assert second["repeat"] is True and second["result"] == first["result"]
    assert planned(get_plan(url, token)) == planned(plan_after_first)
    done = requests.get(f"{url}/api/checkin", headers=auth(token), timeout=20).json()
    assert done["done"] is True and done["result"]["status"] == "low_protein"


def test_before_the_check_in_it_is_not_done(stack):
    fake, url = stack
    token = kitchen_person(url, fake)
    assert requests.get(f"{url}/api/checkin", headers=auth(token), timeout=20).json() == {"done": False, "result": None}


def test_check_in_works_without_a_kitchen(stack):
    fake, url = stack
    token = person(url, None, dietary_preferences=["Vegetarian"])
    fake.reset()
    fake.queue(200, openai_reply("nonsense"))
    plan = get_plan(url, token)
    calories, protein = targets(url, token)
    log(url, token, "Small meal", "lunch", calories=calories // 2, protein=1)
    result = checkin(url, token)["result"]
    assert result["status"] == "low_protein"
    tomorrow = get_plan(url, token)["days"][(plan["today_index"] + 1) % 7]
    assert tomorrow["focus"] == "Protein-forward day" and not (MEAT & {u["id"] for m in tomorrow["meals"] for u in m["uses"]})


def test_check_in_needs_a_plan_a_profile_and_a_sign_in(stack):
    fake, url = stack
    token = person(url, KITCHEN)
    assert requests.post(f"{url}/api/checkin", headers=auth(token), timeout=20).status_code == 404
    assert requests.post(f"{url}/api/checkin", timeout=20).status_code == 401
    assert requests.get(f"{url}/api/checkin", timeout=20).status_code == 401
