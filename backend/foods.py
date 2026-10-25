"""Food catalogue and search, loaded once from data/foods.json (no database, no heavy import).

Every value in the catalogue is an approximate estimate per default serving. Search matches names, family terms
("egg", "dosa"), synonyms and Telugu names, forgives small typos, and ranks: how well it matches first, then how
common the food is, then whether this person logged it recently."""
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

DATA_FILE = Path(__file__).parent / "data" / "foods.json"
COMPACT_DIR = Path(__file__).parent / "data" / "foods"

# Scores: the match decides the tier, popularity and recency only reorder foods inside it.
EXACT_NAME = 100
WORD_EXACT = 85  # a word of the name, a family term or a Telugu word equals what was typed
NAME_PREFIX = 85  # the name starts with what was typed ("egg c" -> "Egg curry")
FAMILY_PREFIX = 65
WORD_PREFIX = 70
SYNONYM_PREFIX = 62
SUBSTRING = 40
FUZZY = 35
POPULAR_STEP = 2  # popular is 0 to 3
RECENT_TOP = 8  # the most recent food gets 8, then 7 ... down to 3
MIN_FUZZY_LENGTH = 4
FUZZY_TRIGGER = 2  # typo tolerance only kicks in when fewer results than this were found without it


def normalize(text: str) -> str:
    """Lower-case, and turn everything that is not a letter, mark or digit into a space (Telugu vowel signs are marks)."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    return " ".join("".join(ch if unicodedata.category(ch)[0] in "LMN" else " " for ch in text).split())


def edit_distance(a: str, b: str, limit: int) -> int:
    """Levenshtein distance with adjacent swaps counted as one; stops early once it must exceed `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous, before = list(range(len(b) + 1)), []
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                value = min(value, before[j - 2] + 1)
            current.append(value)
        if min(current) > limit:
            return limit + 1
        before, previous = previous, current
    return previous[-1]


def singular(word: str) -> str:
    """"eggs" -> "egg", "idlis" -> "idli": a plural typed for a food that is listed in the singular."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def allowed_typos(length: int) -> int:
    return 0 if length < MIN_FUZZY_LENGTH else 1 if length <= 5 else 2


class Food:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.id: str = raw["id"]
        self.name_norm = normalize(raw["name"])
        self.name_words = self.name_norm.split()
        self.te_norm = normalize(raw.get("te", ""))
        self.te_words = self.te_norm.split()
        self.cat_words = {form for word in normalize(raw["category"]).split() for form in (word, singular(word))}
        self.bases = [normalize(term) for term in raw.get("base", [])]
        self.synonyms = [normalize(term) for term in raw.get("synonyms", [])]
        self.synonym_words = {word for phrase in self.synonyms for word in phrase.split()}
        self.popular: int = int(raw.get("popular", 0))
        self.order = 0  # position in the file: the file lists the most common foods of a family first, which breaks ties
        self.fuzzy_words = {word for word in self.name_words + sorted(self.synonym_words) + self.bases + self.te_words if len(word) >= MIN_FUZZY_LENGTH}

    def token_score(self, token: str, fuzzy: bool) -> int:
        """How well one typed word matches this food, 0 for no match."""
        best = 0
        if token in self.name_words or token in self.bases or token in self.te_words:
            return WORD_EXACT
        if token in self.synonym_words or token in self.synonyms:
            best = SYNONYM_PREFIX + 8
        if any(word.startswith(token) for word in self.name_words) or any(word.startswith(token) for word in self.te_words):
            best = max(best, WORD_PREFIX)
        if any(base.startswith(token) for base in self.bases):
            best = max(best, FAMILY_PREFIX)
        if token in self.cat_words:
            best = max(best, WORD_EXACT)  # "snacks", "fruits", "drinks" browse a whole category
        if best == 0 and any(word.startswith(token) for word in self.synonym_words):
            best = SYNONYM_PREFIX
        if best == 0 and len(token) >= 3 and (token in self.name_norm or token in self.te_norm or (len(token) >= 4 and any(token in phrase for phrase in self.synonyms))):
            best = SUBSTRING
        if best == 0 and fuzzy:
            allowed = allowed_typos(len(token))
            if allowed:
                for word in self.fuzzy_words:
                    if word[0] != token[0]:
                        continue
                    distance = min(edit_distance(token, word, allowed), edit_distance(token, word[: len(token)], allowed) + (0 if len(word) == len(token) else 1))
                    if distance <= allowed:
                        best = max(best, FUZZY - 5 * distance)
        return best

    def score(self, query: str, tokens: List[str], fuzzy: bool) -> int:
        if query == self.name_norm:
            return EXACT_NAME
        if self.name_norm.startswith(query) or query in self.synonyms:
            return NAME_PREFIX
        total = []
        for token in tokens:
            value = self.token_score(token, fuzzy)
            stem = singular(token)
            if value == 0 and stem != token:
                value = self.token_score(stem, fuzzy)
            if value == 0:
                return 0
            total.append(value)
        return min(total)

    def serving_options(self) -> List[Dict[str, Any]]:
        return [{"label": self.raw["serving"], "factor": 1.0}] + [dict(option) for option in self.raw.get("servings", [])]

    def public(self, recent: bool = False) -> Dict[str, Any]:
        raw = self.raw
        return {
            "id": self.id,
            "name": raw["name"],
            "te": raw.get("te", ""),
            "category": raw["category"],
            "serving": raw["serving"],
            "calories": raw["calories"],
            "protein_g": raw["protein_g"],
            "carbs_g": raw["carbs_g"],
            "fat_g": raw["fat_g"],
            "servings": self.serving_options(),
            "estimate": True,
            "recent": recent,
        }


def slugify(text: str) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", text.lower())).split())


def number(text: str) -> float:
    return float(text) if text.strip() else 0.0


def load_compact(folder: Path, taken_ids: Iterable[str], taken_names: Iterable[str]) -> List[Dict[str, Any]]:
    """Rows of data/foods/*.txt: name|telugu|category|serving|protein|carbs|fat|alcohol|synonyms, one per line.
    Calories are worked out from the macros (4/4/9, alcohol 7), so they always agree. A name already in the catalogue is skipped."""
    ids, names = set(taken_ids), set(taken_names)
    rows: List[Dict[str, Any]] = []
    for path in sorted(folder.glob("*.txt")):
        if path.name.lower() == "readme.txt":
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split("|")]
            parts += [""] * (9 - len(parts))
            name, te, category, serving, protein, carbs, fat, alcohol, synonyms = parts[:9]
            if normalize(name) in names:
                continue
            base, n = slugify(name), 2
            food_id = base
            while food_id in ids:
                food_id, n = f"{base}-{n}", n + 1
            ids.add(food_id)
            names.add(normalize(name))
            p, c, f, a = number(protein), number(carbs), number(fat), number(alcohol)
            row: Dict[str, Any] = {
                "id": food_id,
                "name": name,
                "te": te,
                "category": category,
                "base": [],
                "synonyms": [term.strip() for term in synonyms.split(",") if term.strip()],
                "serving": serving,
                "calories": round(4 * p + 4 * c + 9 * f + 7 * a),
                "protein_g": p,
                "carbs_g": c,
                "fat_g": f,
                "servings": [{"label": "Half portion", "factor": 0.5}, {"label": "1.5 portions", "factor": 1.5}, {"label": "2 portions", "factor": 2.0}],
                "popular": 0,
                "estimate": True,
            }
            if a:
                row["alcohol_g"] = a
            rows.append(row)
    return rows


class Catalogue:
    def __init__(self, path: Path = DATA_FILE, compact_dir: Optional[Path] = COMPACT_DIR):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.note: str = data.get("note", "")
        raws: List[Dict[str, Any]] = list(data["foods"])
        if compact_dir is not None and compact_dir.is_dir():
            raws += load_compact(compact_dir, [raw["id"] for raw in raws], [normalize(raw["name"]) for raw in raws])
        self.foods: List[Food] = [Food(raw) for raw in raws]
        for position, food in enumerate(self.foods):
            food.order = position
        self.by_id: Dict[str, Food] = {food.id: food for food in self.foods}
        self.by_name: Dict[str, Food] = {food.name_norm: food for food in self.foods}

    def find_by_name(self, name: str) -> Optional[Food]:
        return self.by_name.get(normalize(name))

    def popular(self, limit: int) -> List[Food]:
        ranked = sorted(self.foods, key=lambda food: (-food.popular, food.order))
        return ranked[:limit]

    def search(self, text: str, limit: int = 20, recent_names: Iterable[str] = ()) -> List[Dict[str, Any]]:
        """Ranked matches. `recent_names` are the person's recently logged food names, most recent first."""
        query = normalize(text)
        tokens = query.split()
        if not tokens:
            return []
        recent_rank = {}
        for position, name in enumerate(recent_names):
            recent_rank.setdefault(normalize(name), position)

        def rank(fuzzy: bool) -> List[Tuple[int, Food]]:
            found = []
            for food in self.foods:
                match = food.score(query, tokens, fuzzy)
                if match:
                    found.append((match, food))
            return found

        found = rank(False)
        if len(found) < FUZZY_TRIGGER:
            found = rank(True)

        def order(item: Tuple[int, Food]):
            match, food = item
            position = recent_rank.get(food.name_norm)
            recency = max(RECENT_TOP - position, RECENT_TOP - 5) if position is not None else 0
            return (-(match + food.popular * POPULAR_STEP + recency), food.order)

        found.sort(key=order)
        return [food.public(recent=food.name_norm in recent_rank) for _, food in found[:limit]]


catalogue = Catalogue()
