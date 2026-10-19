"""The kitchen plan engine: meals built from what a person has at home.

Dishes come from data/dishes.json. A dish is chosen only if its ingredients are in the kitchen (or the person's pantry
basics), with at most one missing ingredient, and at most MAX_EXTRAS different "also buy" items across the whole week.
The same engine answers the AI-busy case, "swap this meal" and tomorrow's adaptation, so none of them need the AI.

It never imports server.py: the caller passes in how to size a meal's nutrition."""
import hashlib
import json
import zlib
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

import foods
import kitchen as kitchen_data

DISHES_FILE = Path(__file__).parent / "data" / "dishes.json"
MAX_EXTRAS = 4  # different items on the "also buy" list for a whole week
SLOT_ORDER = ("breakfast", "lunch", "snack", "dinner")
MAIN_SLOTS = ("breakfast", "lunch", "dinner")
COOK_ORDER = ("lunch", "dinner", "breakfast")  # the first N of these are the meals cooked at home
MINUTES_CAP = {"Under 15 min": 15, "20–30 min": 30, "I enjoy cooking": 90}
NO_COOK_MINUTES = 10
SNACK_MINUTES = 15
BUDGET_COST_CAP = {"Budget-friendly": 2}
FALLBACK_BY_GROUP = {
    "vegetables": ["tomato", "potato", "carrot", "cabbage", "beans", "onion"],
    "leafy": ["spinach"],
    "fruits": ["banana", "apple", "papaya"],
}
# What a typical Indian home has, for a person who has not set up their kitchen (swaps and adjustments still work).
DEFAULT_KITCHEN = [
    "rice", "wheat-flour", "toor-dal", "moong-dal", "onion", "tomato", "potato", "carrot", "cabbage", "okra", "brinjal", "spinach",
    "curd", "milk", "banana", "apple", "peanuts", "poha", "semolina", "oats", "bread", "besan", "green-peas", "cauliflower", "beans",
    "idli-batter", "sprouts", "egg", "paneer", "chicken", "fish", "cucumber", "buttermilk", "jaggery", "coconut",
]
FOCUS = "Protein + fibre balance"
PROTEIN_FOCUS = "Protein-forward day"

Portion = Callable[[Dict[str, Any], str, int], Dict[str, Any]]


def kitchen_signature(doc: Optional[Dict[str, Any]]) -> Optional[str]:
    """Changes whenever something that shapes the plan changes; None when there is no kitchen to plan from."""
    if not doc or not doc.get("items"):
        return None
    basis = {"items": sorted(doc["items"]), "meals": doc.get("meals_per_day", 3), "time": doc.get("cooking_time")}
    return hashlib.sha1(json.dumps(basis, sort_keys=True).encode()).hexdigest()[:12]


class Need:
    def __init__(self, raw: Dict[str, Any]):
        self.var: str = raw.get("var", "")
        self.alts: List[str] = raw["alts"]


class Dish:
    def __init__(self, raw: Dict[str, Any]):
        self.name: str = raw["name"]
        self.te: str = raw.get("te", "")
        self.slots: Set[str] = set(raw["slots"])
        self.needs = [Need(n) for n in raw["needs"]]
        self.uses: List[str] = raw.get("uses", [])
        self.minutes: int = raw["minutes"]
        self.cost: int = raw["cost"]


_dishes: Optional[List[Dish]] = None


def dishes() -> List[Dish]:
    global _dishes
    if _dishes is None:
        _dishes = [Dish(raw) for raw in json.loads(DISHES_FILE.read_text(encoding="utf-8"))["dishes"]]
    return _dishes


class Context:
    """What one person's plan may use."""

    def __init__(self, profile: Dict[str, Any], kitchen_doc: Optional[Dict[str, Any]], default_kitchen: bool = False):
        self.profile = profile
        preferences = profile.get("dietary_preferences", [])
        self.exclusions = kitchen_data.profile_exclusions(profile)
        visible = kitchen_data.catalogue.visible(preferences, self.exclusions)
        self.allowed: Set[str] = {item.id for item in visible}
        items = list((kitchen_doc or {}).get("items") or [])
        self.from_default = False
        if not items and default_kitchen:
            items, self.from_default = list(DEFAULT_KITCHEN), True
        self.kitchen_ids: Set[str] = {iid for iid in items if iid in self.allowed}
        self.assumed: Set[str] = {item.id for item in kitchen_data.catalogue.items if item.assumed and item.id in self.allowed}
        self.available: Set[str] = self.kitchen_ids | self.assumed
        # Catalogue order keeps choices stable from one run to the next.
        self.order: List[str] = [item.id for item in kitchen_data.catalogue.items if item.id in self.available]
        self.cooking_time = (kitchen_doc or {}).get("cooking_time") or profile.get("cooking_time") or "20–30 min"
        self.minutes_cap = MINUTES_CAP.get(self.cooking_time, 30)
        self.cost_cap = BUDGET_COST_CAP.get(str(profile.get("food_budget", "")), 3)
        meals = int((kitchen_doc or {}).get("meals_per_day") or 3)
        self.cooked: Set[str] = set(COOK_ORDER[: max(1, min(3, meals))])
        self.household = int((kitchen_doc or {}).get("household_size") or 2)
        self.signature = kitchen_signature(kitchen_doc)

    def blocked_name(self, name: str) -> bool:
        words = set(foods.normalize(name).split())
        return any(foods.normalize(term) and set(foods.normalize(term).split()) <= words for term in self.exclusions)


def make_context(profile: Dict[str, Any], kitchen_doc: Optional[Dict[str, Any]], default_kitchen: bool = False) -> Optional[Context]:
    """A context when there is a kitchen to plan from (or default_kitchen=True), else None."""
    if not (kitchen_doc and kitchen_doc.get("items")) and not default_kitchen:
        return None
    return Context(profile, kitchen_doc, default_kitchen)


class State:
    """What the week has used so far, to keep it varied and the also-buy list short."""

    def __init__(self, extras: Iterable[str] = (), used_names: Iterable[str] = ()):
        self.extras: List[str] = list(dict.fromkeys(extras))
        self.name_counts: Dict[str, int] = {}
        for name in used_names:
            self.name_counts[name] = self.name_counts.get(name, 0) + 1
        self.ingredient_counts: Dict[str, int] = {}
        self.recent_names: List[str] = []  # newest last

    def note(self, meal: Dict[str, Any]) -> None:
        self.name_counts[meal["dish"]] = self.name_counts.get(meal["dish"], 0) + 1
        self.recent_names.append(meal["dish"])
        for iid in meal["ingredients"]:
            self.ingredient_counts[iid] = self.ingredient_counts.get(iid, 0) + 1
        for iid in meal["extras"]:
            if iid not in self.extras:
                self.extras.append(iid)


def short(iid: str, field: str = "name") -> str:
    item = kitchen_data.catalogue.by_id[iid]
    text = item.raw.get("te") if field == "te" and item.raw.get("te") else item.name
    return text.split("(")[0].strip() if field == "name" else text


def render(template: str, bound: Dict[str, str], field: str) -> str:
    text = template.format(**{var: (short(iid, field).lower() if field == "name" else short(iid, field)) for var, iid in bound.items()})
    return text[:1].upper() + text[1:] if field == "name" else text


def resolve(dish: Dish, ctx: Context, rotation: int, state: State) -> Optional[Dict[str, Any]]:
    """The dish made from this kitchen, or None when it cannot be (too much missing, or off the person's diet)."""
    bound: Dict[str, str] = {}
    used: List[str] = []
    missing: List[str] = []
    for need in dish.needs:
        pool: List[str] = []
        for alt in need.alts:
            if alt.startswith("@"):
                pool += [iid for iid in ctx.order if kitchen_data.catalogue.by_id[iid].group == alt[1:] and iid in ctx.kitchen_ids]
            elif alt in ctx.available:
                pool.append(alt)
        pool = list(dict.fromkeys(pool))
        if pool:
            # Rotate through what is there, and prefer what the week has used least.
            ranked = sorted(range(len(pool)), key=lambda i: (state.ingredient_counts.get(pool[i], 0), (i - rotation) % len(pool)))
            choice = pool[ranked[0]]
        else:
            options: List[str] = []
            for alt in need.alts:
                options += FALLBACK_BY_GROUP.get(alt[1:], []) if alt.startswith("@") else [alt]
            choice = next((o for o in options if o in ctx.allowed), "")
            if not choice:
                return None
            missing.append(choice)
        if need.var:
            bound[need.var] = choice
        used.append(choice)
    if len(missing) > 1:
        return None
    if missing and missing[0] not in state.extras and len(state.extras) >= MAX_EXTRAS:
        return None
    name = render(dish.name, bound, "name")
    if ctx.blocked_name(name):
        return None
    optional = [u for u in dish.uses if u in ctx.kitchen_ids and u not in used][:3]
    protein = any(kitchen_data.catalogue.by_id[iid].protein for iid in used)
    return {
        "dish": dish.name,
        "name": name,
        "te": render(dish.te, bound, "te") if dish.te else "",
        "ingredients": list(dict.fromkeys(used + optional)),
        "extras": missing,
        "minutes": dish.minutes,
        "protein": protein,
        "optional": len(optional),
    }


def eligible(dish: Dish, slot: str, ctx: Context) -> bool:
    if dish.cost > ctx.cost_cap:
        return False
    if slot == "snack":
        return "snack" in dish.slots and dish.minutes <= SNACK_MINUTES
    if slot in ctx.cooked:
        return slot in dish.slots and dish.minutes <= ctx.minutes_cap
    # A main meal the person does not cook at home: only something quick with no real cooking.
    return bool(dish.slots & {slot, "snack"}) and dish.minutes <= NO_COOK_MINUTES


def score(meal: Dict[str, Any], day_index: int, slot: str, state: State, prefer_protein: bool) -> float:
    value = 100.0 - 25 * len(meal["extras"]) + 4 * meal["optional"]
    value -= 18 * state.name_counts.get(meal["dish"], 0)
    if meal["dish"] in state.recent_names[-6:]:
        value -= 10
    value -= 2 * sum(state.ingredient_counts.get(iid, 0) for iid in meal["ingredients"][:3]) / max(1, len(meal["ingredients"][:3]))
    if prefer_protein and meal["protein"]:
        value += 14
    # A fixed, repeatable nudge so equal dishes do not always come out in file order.
    value += zlib.crc32(f"{meal['dish']}:{day_index}:{slot}".encode()) % 7 / 7.0 * 3
    return value


def rank(ctx: Context, slot: str, day_index: int, state: State, prefer_protein: bool = False, exclude: Iterable[str] = ()) -> List[Dict[str, Any]]:
    """Every dish that works for this slot, best first."""
    blocked = {foods.normalize(name) for name in exclude}
    slot_number = SLOT_ORDER.index(slot) if slot in SLOT_ORDER else 0
    options = []
    for dish in dishes():
        if not eligible(dish, slot, ctx):
            continue
        meal = resolve(dish, ctx, day_index * 2 + slot_number, state)
        if meal and foods.normalize(meal["name"]) not in blocked and foods.normalize(dish.name) not in blocked:
            options.append((score(meal, day_index, slot, state, prefer_protein), meal))
    options.sort(key=lambda pair: -pair[0])
    return [meal for _, meal in options]


GENERIC = {
    "breakfast": ("Simple breakfast from your kitchen", "మీ వంటగదిలోని వాటితో సాధారణ అల్పాహారం"),
    "lunch": ("Simple home meal from your kitchen", "మీ వంటగదిలోని వాటితో సాధారణ భోజనం"),
    "snack": ("Fruit or a handful of nuts", "పండు లేదా కొన్ని గింజలు"),
    "dinner": ("Light home meal from your kitchen", "మీ వంటగదిలోని వాటితో తేలికపాటి భోజనం"),
}


def finish_meal(meal: Optional[Dict[str, Any]], slot: str, profile: Dict[str, Any], day_index: int, portion: Portion) -> Dict[str, Any]:
    """A plan meal: the dish plus its nutrition, sized from the person's target for this meal."""
    base = meal or {"name": GENERIC[slot][0], "te": GENERIC[slot][1], "ingredients": [], "extras": [], "minutes": 10}
    return {
        "type": slot,
        "name": base["name"],
        "dish": base.get("dish", base["name"]),
        "te": base["te"],
        **portion(profile, slot, day_index),
        "ingredients": base["ingredients"],
        "extras": base["extras"],
        "minutes": base["minutes"],
        "logged": False,
    }


def build_day(ctx: Context, profile: Dict[str, Any], portion: Portion, day_index: int, state: State, prefer_protein: bool = False) -> Dict[str, Any]:
    meals = []
    for slot in SLOT_ORDER:
        choices = rank(ctx, slot, day_index, state, prefer_protein)
        chosen = choices[0] if choices else None
        if chosen:
            state.note(chosen)
        meals.append(finish_meal(chosen, slot, profile, day_index, portion))
    return {"day": day_index + 1, "title": f"Day {day_index + 1}", "focus": PROTEIN_FOCUS if prefer_protein else FOCUS, "meals": meals}


def build_week(ctx: Context, profile: Dict[str, Any], portion: Portion) -> Dict[str, Any]:
    """The deterministic seven-day plan from this kitchen."""
    state = State()
    days = [build_day(ctx, profile, portion, index, state) for index in range(7)]
    return {
        "goal": profile.get("wellness_goal", "Healthier living"),
        "days": days,
        "reasoning": "Every meal is built from what you already have at home, with only a few things to buy, so there is little waste and little shopping.",
        "generated_by": "Wellstride kitchen engine",
        "kitchen_based": True,
        "kitchen_hash": ctx.signature,
        "also_buy": list(state.extras),
    }


def plan_extras(days: List[Dict[str, Any]]) -> List[str]:
    return list(dict.fromkeys(iid for day in days for meal in day.get("meals", []) for iid in meal.get("extras", [])))


def alternatives(ctx: Context, profile: Dict[str, Any], portion: Portion, plan: Dict[str, Any], day_index: int, slot: str, count: int = 3, prefer_protein: bool = False) -> List[Dict[str, Any]]:
    """Other meals for this slot from the same kitchen, none of them the one already planned."""
    days = plan.get("days") or []
    current = next((m for m in (days[day_index].get("meals", []) if day_index < len(days) else []) if m.get("type") == slot), {})
    state = State(extras=plan_extras(days), used_names=[m.get("dish") or m["name"] for d in days for m in d.get("meals", [])])
    choices = rank(ctx, slot, day_index, state, prefer_protein, exclude=[current.get("name", "")])
    picked, seen = [], set()
    for meal in choices:
        if meal["dish"] in seen:
            continue
        seen.add(meal["dish"])
        picked.append(finish_meal(meal, slot, profile, day_index, portion))
        if len(picked) >= count:
            break
    return picked


def rebuild_day(ctx: Context, profile: Dict[str, Any], portion: Portion, plan: Dict[str, Any], day_index: int, prefer_protein: bool) -> Dict[str, Any]:
    """One day of an existing plan, made again (for example with more protein), keeping the rest of the week's variety."""
    days = plan.get("days") or []
    others = [m.get("dish") or m["name"] for i, d in enumerate(days) if i != day_index for m in d.get("meals", [])]
    state = State(extras=plan_extras([d for i, d in enumerate(days) if i != day_index]), used_names=others)
    day = build_day(ctx, profile, portion, day_index, state, prefer_protein)
    day["day"] = days[day_index].get("day", day_index + 1) if day_index < len(days) else day["day"]
    day["title"] = days[day_index].get("title", day["title"]) if day_index < len(days) else day["title"]
    return day
