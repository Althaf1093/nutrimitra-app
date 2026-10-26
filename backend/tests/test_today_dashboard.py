"""Design run, Today: macro totals and targets and the water log on the dashboard."""
import requests

from test_kitchen_daily import log
from test_kitchen_plan import auth, person, stack  # noqa: F401  (stack is a fixture)


def dashboard(url, token):
    response = requests.get(f"{url}/api/dashboard", headers=auth(token), timeout=20)
    assert response.status_code == 200, response.text
    return response.json()


def water(url, token, delta):
    return requests.post(f"{url}/api/water", json={"delta_ml": delta}, headers=auth(token), timeout=20)


def test_dashboard_has_macro_totals_and_targets(stack):
    _, url = stack
    token = person(url, None)
    empty = dashboard(url, token)
    assert (empty["protein_g"], empty["carbs_g"], empty["fat_g"]) == (0, 0, 0)
    # The three macro targets add up to (about) the calorie target.
    energy = empty["target_protein_g"] * 4 + empty["target_carbs_g"] * 4 + empty["target_fat_g"] * 9
    assert abs(energy - empty["target_calories"]) <= 12
    log(url, token, "Dal rice", calories=500, protein=20)
    log(url, token, "Curd", meal_type="snack", calories=100, protein=8)
    later = dashboard(url, token)
    assert later["protein_g"] == 28 and later["carbs_g"] == 100 and later["fat_g"] == 20


def test_water_adds_up_never_goes_below_zero_and_shows_on_the_dashboard(stack):
    _, url = stack
    token = person(url, None)
    assert dashboard(url, token)["water_ml"] == 0
    assert dashboard(url, token)["target_water_ml"] % 250 == 0
    assert water(url, token, 250).json()["water_ml"] == 250
    assert water(url, token, 500).json()["water_ml"] == 750
    assert dashboard(url, token)["water_ml"] == 750
    assert water(url, token, -2000).json()["water_ml"] == 0


def test_water_rejects_absurd_amounts_and_needs_sign_in(stack):
    _, url = stack
    token = person(url, None)
    assert water(url, token, 5000).status_code == 422
    assert requests.post(f"{url}/api/water", json={"delta_ml": 250}, timeout=20).status_code in (401, 403)


def test_fibre_shows_only_when_a_meal_has_it(stack):
    _, url = stack
    token = person(url, None)
    empty = dashboard(url, token)
    assert empty["fibre_tracked"] is False and empty["fibre_g"] == 0 and empty["target_fibre_g"] > 0
    log(url, token, "Dal rice", calories=500, protein=20)
    assert dashboard(url, token)["fibre_tracked"] is False
    body = {"meal_type": "snack", "name": "Chana", "calories": 150, "protein_g": 8, "carbs_g": 20, "fat_g": 3, "fibre_g": 7}
    assert requests.post(f"{url}/api/meals", json=body, headers=auth(token), timeout=20).status_code == 200
    later = dashboard(url, token)
    assert later["fibre_tracked"] is True and later["fibre_g"] == 7


def test_version_endpoint_returns_the_git_commit(stack):
    import subprocess
    from pathlib import Path

    _, url = stack
    response = requests.get(f"{url}/api/version", timeout=20)
    assert response.status_code == 200
    commit = response.json()["commit"]
    expected = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).parent, capture_output=True, text=True).stdout.strip()
    assert commit == expected and len(commit) >= 7


def test_fibre_flows_from_the_catalogue_to_the_dashboard_and_can_be_edited(stack):
    _, url = stack
    token = person(url, None)
    found = requests.get(f"{url}/api/foods/search", params={"q": "rajma masala"}, headers=auth(token), timeout=20).json()
    food = next(item for item in found["results"] if item["name"] == "Rajma masala") if isinstance(found, dict) else next(item for item in found if item["name"] == "Rajma masala")
    assert food["fibre_g"] >= 8
    body = {"meal_type": "lunch", "name": food["name"], "calories": food["calories"], "protein_g": food["protein_g"], "carbs_g": food["carbs_g"], "fat_g": food["fat_g"], "fibre_g": food["fibre_g"]}
    saved = requests.post(f"{url}/api/meals", json=body, headers=auth(token), timeout=20).json()
    assert dashboard(url, token)["fibre_g"] == round(food["fibre_g"])
    edited = requests.patch(f"{url}/api/meals/{saved['id']}", json={"fibre_g": 3}, headers=auth(token), timeout=20)
    assert edited.status_code == 200
    assert dashboard(url, token)["fibre_g"] == 3
