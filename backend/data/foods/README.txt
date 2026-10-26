Compact food rows, one per line, loaded at startup next to ../foods.json (see foods.py, load_compact).
Fields separated by "|": name | telugu | category | serving | protein_g | carbs_g | fat_g | alcohol_g | fibre_g | synonyms (comma separated)
Fibre (g per serving, estimated by tools/add_fibre.py from the food type) is informational and not part of the calories.
Calories are worked out as 4*protein + 4*carbs + 9*fat + 7*alcohol, so calories and macros always agree.
Every value is an estimate per serving (estimate: true). Lines starting with # are comments.
Sources and licences: docs/FOOD_DATA_SOURCES.md
