"""My Kitchen: the ingredient catalogue (data/ingredients.json) and which of it a person may see.

A vegetarian never sees chicken: every ingredient has a diet level, and the person's dietary preference sets the highest level
that is shown, and accepted when they save their kitchen. Allergies and foods they avoid are hidden too."""
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import foods

DATA_FILE = Path(__file__).parent / "data" / "ingredients.json"

# vegan < vegetarian < eggetarian < everything. The strictest preference the person chose wins, like the plan safety net.
DIET_RANK = {"vegan": 0, "veg": 1, "egg": 2, "non": 3}
PREFERENCE_RANK = {"vegan": 0, "vegetarian": 1, "eggetarian": 2, "non-vegetarian": 3, "non vegetarian": 3}
GROUPS = ["vegetables", "leafy", "staples", "pulses", "protein", "dairy", "fruits", "oils", "extras", "pantry"]
COOKING_TIMES = ["Under 15 min", "20–30 min", "I enjoy cooking"]
MAX_ITEMS = 250
MIN_MEALS, MAX_MEALS = 1, 3
MIN_PEOPLE, MAX_PEOPLE = 1, 12


def max_diet_rank(preferences: Iterable[str]) -> int:
    """The highest diet level a person may see. No stated preference means no limit."""
    ranks = [PREFERENCE_RANK[p.strip().lower()] for p in preferences if str(p).strip().lower() in PREFERENCE_RANK]
    return min(ranks) if ranks else DIET_RANK["non"]


def words(text: str) -> List[str]:
    return foods.normalize(text).split()


def singular(word: str) -> str:
    return foods.singular(word)


class Ingredient:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.id: str = raw["id"]
        self.name: str = raw["name"]
        self.group: str = raw["group"]
        self.rank: int = DIET_RANK[raw["diet"]]
        self.protein: bool = bool(raw.get("protein"))
        self.assumed: bool = bool(raw.get("assumed"))
        # The full name, the name without its bracket ("Rice (white)" -> "rice"), and every alias.
        self.labels = list(dict.fromkeys([foods.normalize(raw["name"]), foods.normalize(raw["name"].split("(")[0])] + [foods.normalize(a) for a in raw.get("aliases", [])]))
        # Every word of the name and aliases, singular and plural, so "peanut" finds "Peanuts" and "eggs" finds "Egg".
        self.word_set: Set[str] = {w for label in self.labels for w in label.split()} | {singular(w) for label in self.labels for w in label.split()}

    def public(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "te": self.raw.get("te", ""), "group": self.group, "diet": self.raw["diet"], "aliases": self.raw.get("aliases", []), "protein": self.protein, "assumed": self.assumed}

    def matches_term(self, term: str) -> bool:
        """True when a typed term (an allergy, a dislike, a search) names this ingredient: all its words are among ours."""
        parts = [singular(w) for w in words(term)]
        return bool(parts) and all(part in self.word_set for part in parts)


class IngredientCatalogue:
    def __init__(self, path: Path = DATA_FILE):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.items: List[Ingredient] = [Ingredient(raw) for raw in data["ingredients"]]
        self.by_id: Dict[str, Ingredient] = {item.id: item for item in self.items}
        self.by_label: Dict[str, Ingredient] = {}
        for item in self.items:
            for label in item.labels:
                self.by_label.setdefault(label, item)
                self.by_label.setdefault(" ".join(singular(w) for w in label.split()), item)

    def find(self, name: str) -> Optional[Ingredient]:
        """The ingredient a name (English, as the plan generator writes it) refers to, or None."""
        text = foods.normalize(name)
        if text in self.by_label:
            return self.by_label[text]
        return self.by_label.get(" ".join(singular(w) for w in text.split()))

    def blocked_by(self, item: Ingredient, exclusions: Iterable[str]) -> bool:
        return any(item.matches_term(term) for term in exclusions if str(term).strip())

    def visible(self, preferences: Iterable[str], exclusions: Iterable[str] = ()) -> List[Ingredient]:
        """What this person may pick: within their diet, and not something they are allergic to or avoid."""
        limit = max_diet_rank(preferences)
        exclusions = [e for e in exclusions if str(e).strip()]
        return [item for item in self.items if item.rank <= limit and not self.blocked_by(item, exclusions)]

    def search(self, items: List[Ingredient], query: str) -> List[Ingredient]:
        text = foods.normalize(query)
        if not text:
            return items
        parts = [singular(w) for w in text.split()]
        return [item for item in items if all(any(w.startswith(part) for w in item.word_set) for part in parts)]


catalogue = IngredientCatalogue()


def profile_exclusions(profile: Optional[Dict[str, Any]]) -> List[str]:
    profile = profile or {}
    return [str(x) for x in (profile.get("allergies") or []) + (profile.get("disliked_foods") or []) if str(x).strip()]


def clean_kitchen_items(ids: Iterable[str], preferences: Iterable[str], exclusions: Iterable[str] = ()) -> Tuple[List[str], List[str]]:
    """Split saved ids into (kept, problems): unknown ids, and ids outside the person's diet or allergy list."""
    allowed = {item.id for item in catalogue.visible(preferences, exclusions)}
    kept, problems, seen = [], [], set()
    for raw in ids:
        iid = str(raw).strip()
        if iid in seen:
            continue
        seen.add(iid)
        if iid not in catalogue.by_id:
            problems.append(f"Unknown ingredient: {iid[:40]}")
        elif iid not in allowed:
            problems.append(f"{catalogue.by_id[iid].name} is not part of your diet or food list")
        else:
            kept.append(iid)
    return kept, problems
