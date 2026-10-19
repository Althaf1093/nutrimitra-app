import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import { api } from "@/src/api";
import { Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { optionLabel, type Copy } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { Ingredient } from "@/src/types";

export type KitchenDraft = { items: string[]; meals_per_day: number; household_size: number; cooking_time: string };

export const COOKING_TIMES = ["Under 15 min", "20–30 min", "I enjoy cooking"];
const MEALS = [1, 2, 3];
const PEOPLE = [1, 2, 3, 4, 5, 6];
// Ingredient groups shown in the editor, with their label keys. "pantry" (salt, spices) is assumed, never picked.
const GROUPS: { id: string; label: keyof Copy }[] = [
  { id: "vegetables", label: "groupVegetables" },
  { id: "leafy", label: "groupLeafy" },
  { id: "staples", label: "groupStaples" },
  { id: "pulses", label: "groupPulses" },
  { id: "protein", label: "groupProtein" },
  { id: "dairy", label: "groupDairy" },
  { id: "fruits", label: "groupFruits" },
  { id: "oils", label: "groupOils" },
  { id: "extras", label: "groupExtras" },
];

const matches = (item: Ingredient, query: string) => {
  const text = query.trim().toLowerCase();
  if (!text) return true;
  return [item.name, item.te, ...item.aliases].some((label) => label.toLowerCase().includes(text));
};

// What is in your kitchen, how many meals you cook, for how many people, and how long you want to cook.
// `diet` and `exclude` are the choices from onboarding (no profile is saved yet); in Settings leave them out and the server uses the profile.
export function KitchenEditor({ value, onChange, diet, exclude }: { value: KitchenDraft; onChange: (next: KitchenDraft) => void; diet?: string[]; exclude?: string[] }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const { lang, t } = useAuth();
  const [ingredients, setIngredients] = useState<Ingredient[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState("");
  const [closed, setClosed] = useState<Record<string, boolean>>({});
  const dietKey = diet ? diet.join(",") : null;
  const excludeKey = exclude ? exclude.join(",") : null;

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams();
    if (dietKey !== null) params.set("diet", dietKey);
    if (excludeKey !== null) params.set("exclude", excludeKey);
    api<{ ingredients: Ingredient[] }>(`/kitchen/ingredients?${params.toString()}`)
      .then((result) => {
        if (cancelled) return;
        setFailed(false);
        setIngredients(result.ingredients.filter((item) => !item.assumed));
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [dietKey, excludeKey]);

  const label = (item: Ingredient) => (lang === "te" && item.te ? item.te : item.name);
  const chosen = useMemo(() => new Set(value.items), [value.items]);
  const toggle = (id: string) => onChange({ ...value, items: chosen.has(id) ? value.items.filter((item) => item !== id) : [...value.items, id] });
  // Items that no longer fit the diet (it may have changed on the previous step) drop out of the count and of what is saved.
  const visibleIds = useMemo(() => new Set((ingredients ?? []).map((item) => item.id)), [ingredients]);
  const selectedCount = value.items.filter((id) => visibleIds.has(id)).length;
  const searching = query.trim().length > 0;
  const found = (ingredients ?? []).filter((item) => matches(item, query));

  const chip = (item: Ingredient) => <Chip key={item.id} label={item.id} text={label(item)} selected={chosen.has(item.id)} onPress={() => toggle(item.id)} />;

  return (
    <View testID="kitchen-editor">
      <Text style={styles.sectionTitleSmall}>{t.kitchenTitle}</Text>
      <Text style={styles.modalSub}>{t.kitchenSub}</Text>
      <View style={styles.searchBar}>
        <TextInput testID="kitchen-search" accessibilityLabel={t.kitchenSearch} value={query} onChangeText={setQuery} placeholder={t.kitchenSearch} placeholderTextColor={colors.muted} autoCorrect={false} autoCapitalize="none" style={styles.searchInput} />
        {query ? (
          <Pressable testID="kitchen-search-clear" accessibilityRole="button" accessibilityLabel={t.clearSearch} onPress={() => setQuery("")} style={styles.searchClear}>
            <Text style={styles.searchClearText}>✕</Text>
          </Pressable>
        ) : null}
      </View>
      <View style={[styles.row, { alignItems: "center", marginTop: 10 }]}>
        <Text style={[styles.mutedText, styles.flex]} testID="kitchen-count">
          {selectedCount} {t.kitchenSelectedCount}
        </Text>
        {selectedCount > 0 ? (
          <Pressable testID="kitchen-clear" accessibilityRole="button" onPress={() => onChange({ ...value, items: [] })} style={styles.linkButton}>
            <Text style={styles.linkText}>{t.kitchenClear}</Text>
          </Pressable>
        ) : null}
      </View>

      {ingredients === null && !failed ? <ActivityIndicator color={colors.brandPrimary} style={{ marginVertical: 24 }} /> : null}
      {failed ? (
        <View style={styles.reasonCard} testID="kitchen-load-failed">
          <Text style={styles.reasonText}>{t.kitchenLoadFailed}</Text>
        </View>
      ) : null}
      {ingredients && searching ? (
        found.length ? (
          <View style={[styles.chipWrap, { marginTop: 8 }]} testID="kitchen-results">
            {found.map(chip)}
          </View>
        ) : (
          <Text style={styles.mutedText} testID="kitchen-no-match">
            {t.kitchenNoMatch}
          </Text>
        )
      ) : null}
      {ingredients && !searching
        ? GROUPS.map((group) => {
            const members = ingredients.filter((item) => item.group === group.id);
            if (!members.length) return null;
            const picked = members.filter((item) => chosen.has(item.id)).length;
            const open = !closed[group.id];
            return (
              <View key={group.id} testID={`kitchen-group-${group.id}`}>
                <Pressable accessibilityRole="button" accessibilityState={{ expanded: open }} testID={`kitchen-group-toggle-${group.id}`} onPress={() => setClosed((current) => ({ ...current, [group.id]: open }))} style={[styles.row, { alignItems: "center", marginTop: 14, marginBottom: 8, minHeight: 36 }]}>
                  <Text style={[styles.fieldLabel, styles.flex, { marginTop: 0, marginBottom: 0 }]}>
                    {t[group.label] as string}
                    {picked ? ` · ${picked}` : ""}
                  </Text>
                  <Text style={styles.mutedText}>{open ? "−" : "+"}</Text>
                </Pressable>
                {open ? <View style={styles.chipWrap}>{members.map(chip)}</View> : null}
              </View>
            );
          })
        : null}

      <Text style={[styles.fieldLabel, { marginTop: 18 }]}>{t.kitchenMeals}</Text>
      <View style={styles.chipWrap}>
        {MEALS.map((count) => (
          <Chip key={count} label={`meals-${count}`} text={String(count)} selected={value.meals_per_day === count} onPress={() => onChange({ ...value, meals_per_day: count })} />
        ))}
      </View>
      <Text style={styles.fieldLabel}>{t.kitchenPeople}</Text>
      <View style={styles.chipWrap}>
        {PEOPLE.map((count) => (
          <Chip key={count} label={`people-${count}`} text={count === 6 ? "6+" : String(count)} selected={value.household_size === count} onPress={() => onChange({ ...value, household_size: count })} />
        ))}
      </View>
      <Text style={styles.fieldLabel}>{t.kitchenCookTime}</Text>
      <View style={styles.chipWrap}>
        {COOKING_TIMES.map((item) => (
          <Chip key={item} label={item} text={optionLabel(t, item)} selected={value.cooking_time === item} onPress={() => onChange({ ...value, cooking_time: item })} />
        ))}
      </View>
    </View>
  );
}
