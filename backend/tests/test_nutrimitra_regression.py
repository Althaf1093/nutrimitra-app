import os
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
EMAIL = "preview.user.2026@example.com"
PASSWORD = "StrongPass123"


def test_authenticated_core_apis():
    session = requests.Session()
    login = session.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=20)
    assert login.status_code == 200
    token = login.json()["token"]
    session.headers["Authorization"] = f"Bearer {token}"

    for path in ("/me", "/plan", "/dashboard", "/progress", "/permissions"):
        response = session.get(f"{BASE_URL}/api{path}", timeout=30)
        assert response.status_code == 200, (path, response.text)
        assert isinstance(response.json(), (dict, list))

    meal = session.post(f"{BASE_URL}/api/meals", json={"meal_type": "snack", "name": "TEST almonds", "calories": 120, "protein_g": 4, "carbs_g": 5, "fat_g": 10, "source": "manual"}, timeout=20)
    assert meal.status_code == 200
    assert meal.json()["name"] == "TEST almonds"

    activity = session.post(f"{BASE_URL}/api/activities", json={"activity_type": "Walking", "duration_min": 20, "distance_km": 2.1, "active_calories": 120, "source": "manual estimate"}, timeout=20)
    assert activity.status_code == 200
    assert activity.json()["source"] == "manual estimate"

    weight = session.post(f"{BASE_URL}/api/weight", json={"weight_kg": 68.5}, timeout=20)
    assert weight.status_code == 200
    assert weight.json()["weight_kg"] == 68.5

    coach = session.post(f"{BASE_URL}/api/coach", json={"message": "Give a healthy breakfast idea", "language": "en"}, timeout=45)
    assert coach.status_code == 200
    assert isinstance(coach.json().get("reply"), str)


def test_ingredients_global_search():
    response = requests.get(f"{BASE_URL}/api/ingredients?q=avocado", timeout=20)
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Avocado"