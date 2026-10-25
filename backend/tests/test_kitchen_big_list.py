"""Logging run item 4: the big ingredient list and "Snap your kitchen" (POST /api/kitchen/snap), tested against a fake vision provider."""
import json
import uuid

import pytest
import requests
from pymongo import MongoClient

import kitchen
from fakes import FakeProvider, gemini_reply, spawn_backend, stop_backend

KEY = "fake-gemini-key-kitchen"
IMAGE = "/9j/" + "A" * 400


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=10000)
    yield client.test_database
    client.close()


@pytest.fixture(scope="module")
def gemini():
    fake = FakeProvider()
    yield fake
    fake.close()


@pytest.fixture(scope="module")
def backend(gemini, tmp_path_factory):
    url, proc = spawn_backend({"VISION_PROVIDER": "gemini", "GEMINI_API_KEY": KEY, "GEMINI_BASE_URL": gemini.url, "GEMINI_MODEL": "gemini-test-flash", "GROQ_API_KEY": ""}, log_path=tmp_path_factory.mktemp("logs") / "backend.log")
    yield url
    stop_backend(proc)


@pytest.fixture()
def person(backend, mongo):
    resp = requests.post(f"{backend}/api/auth/signup", json={"accept_terms": True, "email": f"snap.{uuid.uuid4().hex[:10]}@example.com", "password": "StrongPass123"}, timeout=20)
    assert resp.status_code == 200, resp.text
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    yield headers
    mongo.users.delete_many({"id": resp.json()["user"]["id"]})


def snap(backend, headers, **extra):
    return requests.post(f"{backend}/api/kitchen/snap", json={"image_base64": IMAGE, **extra}, headers=headers, timeout=60)


# ---- the data ----------------------------------------------------------------------------------------------

def test_catalogue_covers_the_common_ingredients_in_every_group():
    items = kitchen.catalogue.items
    assert len(items) >= 600
    assert len({item.id for item in items}) == len(items)
    groups = {item.group for item in items}
    for needed in ("vegetables", "leafy", "staples", "pulses", "protein", "dairy", "fruits", "oils", "spices", "extras", "condiments"):
        assert needed in groups
        assert needed in kitchen.GROUPS
    for item in items:
        assert item.group in kitchen.GROUPS and item.raw["diet"] in kitchen.DIET_RANK, item.id
        assert item.raw.get("te"), f"{item.id} needs a Telugu name"
    for query in ("basmati", "kale", "ajwain", "salmon", "tempeh", "ragi flour", "garam masala", "soy sauce", "oats", "paneer", "chicken breast", "guntur"):
        assert kitchen.catalogue.search(list(items), query), query


def test_new_meat_and_fish_stay_out_of_a_vegetarian_kitchen():
    visible = {item.id for item in kitchen.catalogue.visible(["Vegetarian"])}
    for item in kitchen.catalogue.items:
        if item.raw["diet"] in ("non", "egg"):
            assert item.id not in visible, item.id
    assert "paneer" in visible and "chicken" not in visible


def test_old_names_still_resolve_to_the_old_ingredients():
    for name, expected in (("Milk", "milk"), ("Chicken", "chicken"), ("Toor dal", "toor-dal"), ("tomato", "tomato")):
        assert kitchen.catalogue.find(name).id == expected


# ---- snap your kitchen ---------------------------------------------------------------------------------------

def reply(gemini, names):
    gemini.queue(200, gemini_reply(json.dumps({"ingredients": names})))


def test_snap_lists_matched_ingredients_and_saves_nothing(backend, gemini, person):
    gemini.reset()
    reply(gemini, ["tomato", "Onion", "toor dal", "basmati rice", "curd", "unicorn tears"])
    response = snap(backend, person)
    assert response.status_code == 200, response.text
    body = response.json()
    matched = {item["id"] for item in body["matches"]}
    assert {"tomato", "onion", "toor-dal", "basmati-rice", "curd"} <= matched
    assert "unicorn tears" in body["unmatched"]
    for item in body["matches"]:
        assert item["name"] and "group" in item
    sent = gemini.requests[-1]["body"]["contents"][0]["parts"]
    assert "ingredients" in sent[0]["text"] and sent[1]["inline_data"]["data"] == IMAGE
    assert requests.get(f"{backend}/api/kitchen", headers=person, timeout=20).json() == {"configured": False, "kitchen": None}


def test_snap_respects_the_diet(backend, gemini, person):
    gemini.reset()
    reply(gemini, ["chicken", "paneer", "egg", "spinach"])
    body = snap(backend, person, diet="Vegetarian").json()
    matched = {item["id"] for item in body["matches"]}
    assert matched == {"paneer", "spinach"}
    assert body["unmatched"] == [], "items outside the diet are dropped quietly, not offered or reported"


def test_snap_removes_duplicates_and_pantry_basics(backend, gemini, person):
    gemini.reset()
    reply(gemini, ["tomato", "tomatoes", "Tomato", "salt", "turmeric"])
    body = snap(backend, person).json()
    assert [item["id"] for item in body["matches"]] == ["tomato"]


def test_snap_when_the_provider_is_busy_is_a_clear_503(backend, gemini, person):
    gemini.reset()
    for _ in range(3):
        gemini.queue(500, {"error": {"message": "busy"}})
    response = snap(backend, person)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "vision_unavailable"
    assert "pick your ingredients" in response.json()["detail"]["message"]


def test_snap_with_a_reply_that_is_not_a_list_is_a_503(backend, gemini, person):
    gemini.reset()
    gemini.queue(200, gemini_reply(json.dumps({"ingredients": "tomato"})))
    assert snap(backend, person).status_code == 503


def test_snap_needs_a_login_and_a_real_image(backend, person):
    assert requests.post(f"{backend}/api/kitchen/snap", json={"image_base64": IMAGE}, timeout=20).status_code in (401, 403)
    assert requests.post(f"{backend}/api/kitchen/snap", json={"image_base64": "x"}, headers=person, timeout=20).status_code == 422


def test_a_big_kitchen_can_be_saved(backend, person):
    chosen = [item.id for item in kitchen.catalogue.items if item.raw["diet"] == "vegan" and not item.assumed][:300]
    assert len(chosen) == 300
    response = requests.put(f"{backend}/api/kitchen", json={"items": chosen, "meals_per_day": 3, "household_size": 2}, headers=person, timeout=20)
    assert response.status_code == 200, response.text
    assert len(response.json()["kitchen"]["items"]) == 300
