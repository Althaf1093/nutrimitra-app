"""Phase 3 item 7: user-visible text lives in src/i18n.ts in English and Telugu.

The app has no UI test harness, so these read the source: key parity, every t.<key> exists, no hard-coded
English left in the screens, and stored option values are unchanged (only their display text is translated)."""
import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
I18N = (FRONTEND / "src" / "i18n.ts").read_text(encoding="utf-8")
EN_BLOCK, TE_BLOCK = I18N.split("  te: {", 1)
KEY_LINE = re.compile(r'^    (\w+): "(.*)",?$', re.M)
EN = dict(KEY_LINE.findall(EN_BLOCK))
TE = dict(KEY_LINE.findall(TE_BLOCK))
TELUGU_LETTER = re.compile("[ఀ-౿]")
SAME_AS_ENGLISH_OK = {"healthTitle", "consentAnd"}  # product names (Apple Health / Health Connect); a bare joining space


def source_files():
    for folder in (FRONTEND / "app", FRONTEND / "src" / "components"):
        for path in folder.rglob("*.tsx"):
            yield path


def all_files():
    yield from source_files()
    yield from (FRONTEND / "src").rglob("*.ts")
    yield from (FRONTEND / "src").rglob("*.tsx")


class TestCatalogue:
    def test_english_and_telugu_have_the_same_keys(self):
        assert len(EN) > 200
        assert set(EN) == set(TE), (sorted(set(EN) - set(TE)), sorted(set(TE) - set(EN)))

    def test_no_empty_values(self):
        # consentAfter is the text after the policy links, which is nothing in English ("I agree to the Terms and Privacy Policy").
        assert [k for k, v in {**EN}.items() if not v.strip() and k != "consentAfter"] == []
        assert [k for k, v in {**TE}.items() if not v.strip() and k != "consentAnd"] == []  # consentAnd is a joining space in Telugu

    def test_telugu_is_actually_telugu(self):
        untranslated = [k for k, v in TE.items() if not TELUGU_LETTER.search(v) and k not in SAME_AS_ENGLISH_OK]
        assert untranslated == [], untranslated
        assert [k for k in TE if TE[k] == EN[k] and k not in SAME_AS_ENGLISH_OK] == []

    def test_placeholders_match_between_languages(self):
        for key, value in EN.items():
            assert sorted(re.findall(r"\{\w+\}", value)) == sorted(re.findall(r"\{\w+\}", TE[key])), key

    def test_every_key_used_in_the_app_exists(self):
        used = set()
        for path in all_files():
            used |= set(re.findall(r"\bt\.([A-Za-z0-9]+)", path.read_text(encoding="utf-8")))
        missing = sorted(key for key in used if key not in EN and key not in {"length", "replace", "toUpperCase", "toLowerCase", "trim"})
        assert missing == [], missing


# Text that may stay in the code: product names, language names, proper nouns and developer-only text.
ALLOWED = {
    "cm",  # units next to the height field
    "ft",
    "Apple Health · Health Connect",
    "English",
    "HealthKit / Health Connect",
    "Hide details | Show details",
    "entry",  # a chart key fallback, not shown
}
ATTR = re.compile(r'\b(label|placeholder|title|subtitle|accessibilityLabel)="([^"{}]*[A-Za-z][^"{}]*)"')
CALL = re.compile(r'\b(?:setMessage|setError|setNotice)\(\s*"([^"]*[A-Za-z][^"]*)"')
FALLBACK = re.compile(r'\|\|\s*"([^"]*[A-Za-z]{3,}[^"]*)"')
JSX_TEXT = re.compile(r">\s*([A-Za-z][^<>{}\n]{1,80}?)\s*<")


class TestNoHardCodedEnglish:
    def hits(self):
        found = []
        for path in source_files():
            if path.name == "error-boundary.tsx":
                continue  # renders both languages from i18n; the only literals are developer-only toggles
            for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
                stripped = line.strip()
                if stripped.startswith(("//", "import ", "*")):
                    continue
                candidates = [m.group(m.lastindex) for rx in (ATTR, CALL, FALLBACK) for m in rx.finditer(line)]
                candidates += [m.group(1) for m in JSX_TEXT.finditer(line) if re.search(r"[a-z]{2}", m.group(1)) and not m.group(1).startswith("t.")]
                for text in candidates:
                    if text not in ALLOWED and not text.startswith("/") and "|" not in text.replace(" | ", "x"):
                        found.append(f"{path.relative_to(FRONTEND).as_posix()}:{number}: {text[:60]}")
        return found

    def test_screens_have_no_hard_coded_english(self):
        assert self.hits() == []

    def test_ternary_language_switches_are_gone(self):
        """Text is chosen through the catalogue, not with inline lang === "te" ? ... : ... ."""
        offenders = []
        for path in source_files():
            for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
                if re.search(r'lang === "te" \? "', line) and TELUGU_LETTER.search(line):
                    offenders.append(f"{path.relative_to(FRONTEND).as_posix()}:{number}")
        assert offenders == [], offenders


class TestSpecificStrings:
    def read(self, *parts):
        return FRONTEND.joinpath(*parts).read_text(encoding="utf-8")

    def test_day_labels_and_back_button(self):
        plan = self.read("app", "(tabs)", "plan.tsx")
        assert "`${t.dayWord} ${item.day}" in plan and "`Day " not in plan
        assert "label={t.back}" in self.read("app", "onboarding.tsx")
        assert EN["back"] == "Back" and EN["dayWord"] == "Day"

    def test_coach_quick_prompts_are_sent_in_the_users_language(self):
        coach = self.read("app", "(tabs)", "coach.tsx")
        for key in ("quickProtein", "quickDinner", "quickLowEnergy"):
            assert f"label={{t.{key}}}" in coach and f"send(t.{key}Prompt)" in coach
            assert TELUGU_LETTER.search(TE[key + "Prompt"]), key

    def test_settings_labels_are_translated(self):
        settings = self.read("app", "settings.tsx")
        for key in ("wearables", "analytics", "analyticsSub", "everyThreeHours", "everyTwoHours", "sundays", "optionalPermission", "notifBlocked", "notifDenied", "statusWeb", "statusBuild"):
            assert f"t.{key}" in settings, key
        assert '"Supported wearables"' not in settings and '"Every 3 hours"' not in settings


class TestBehaviourIsUnchanged:
    """Only display text is translated: stored values (what the backend receives) stay the English ones."""

    def read(self, *parts):
        return FRONTEND.joinpath(*parts).read_text(encoding="utf-8")

    def test_option_values_are_still_english_and_all_have_translations(self):
        onboarding = self.read("app", "onboarding.tsx")
        values = []
        for name in ("goals", "diets", "activityLevels"):
            values += re.findall(r'"([^"]+)"', re.search(rf"const {name} = \[(.*?)\];", onboarding).group(1))
        values += ["Female", "Male", "Prefer not to say", "Under 15 min", "20–30 min", "I enjoy cooking", "Budget-friendly", "Balanced", "Flexible"]
        keys = dict(re.findall(r'^  "?([\w -–]+?)"?: "(\w+)",$', I18N, re.M))
        for value in values:
            assert value in keys, f"{value} has no display translation"
            assert keys[value] in EN and keys[value] in TE
        # the chip identity and the saved value still come from the English item
        assert 'label={item} text={optionLabel(t, item)}' in onboarding
        assert 'set("wellness_goal", item)' in onboarding and 'set("sex", item)' in onboarding

    def test_chip_ids_do_not_change_with_language(self):
        ui = self.read("src", "components", "ui.tsx")
        assert "testID={`chip-${label.toLowerCase()" in ui and "{text ?? label}" in ui

    def test_meal_types_sent_to_the_backend_are_not_translated(self):
        index = self.read("app", "(tabs)", "index.tsx")
        assert "meal_type: meal.type" in self.read("src", "lib", "plan.ts")  # the body index.tsx and plan.tsx send for a plan meal
        assert "planMealBody(meal)" in index
        assert "mealTypeLabel(t, item.meal_type)" in index
