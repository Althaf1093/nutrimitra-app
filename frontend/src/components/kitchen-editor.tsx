import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import { api, post } from "@/src/api";
import { AppIcon, Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { optionLabel, type Copy } from "@/src/i18n";
import { pickPhoto } from "@/src/lib/pick-photo";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { Ingredient, KitchenSnapResult } from "@/src/types";

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
  { id: "spices", label: "groupSpices" },
  { id: "extras", label: "groupExtras" },
  { id: "condiments", label: "groupCondiments" },
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
  const [tab, setTab] = useState("all");
  // "Snap your kitchen": the photo is read, the person ticks what is right, and only then does it join the kitchen.
  const [snap, setSnap] = useState<{ phase: "reading" | "review" | "error"; found: Ingredient[]; unmatched: string[]; keep: Record<string, boolean>; message: string } | null>(null);
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

  const snapKitchen = async () => {
    const photo = await pickPhoto("camera");
    if (photo.status === "cancelled") return;
    if (photo.status === "denied") return setSnap({ phase: "error", found: [], unmatched: [], keep: {}, message: t.cameraBlocked });
    if (photo.status === "failed") return setSnap({ phase: "error", found: [], unmatched: [], keep: {}, message: t.photoFailed });
    setSnap({ phase: "reading", found: [], unmatched: [], keep: {}, message: "" });
    try {
      const body: { image_base64: string; diet?: string; exclude?: string } = { image_base64: photo.base64 };
      if (dietKey !== null) body.diet = dietKey;
      if (excludeKey !== null) body.exclude = excludeKey;
      const result = await post<KitchenSnapResult>("/kitchen/snap", body);
      const keep: Record<string, boolean> = {};
      result.matches.forEach((item) => (keep[item.id] = true));
      setSnap({ phase: "review", found: result.matches, unmatched: result.unmatched, keep, message: "" });
    } catch (err) {
      setSnap({ phase: "error", found: [], unmatched: [], keep: {}, message: err instanceof Error ? err.message : t.photoFailed });
    }
  };
  const addSnapped = () => {
    if (!snap) return;
    const add = snap.found.filter((item) => snap.keep[item.id]).map((item) => item.id);
    onChange({ ...value, items: Array.from(new Set([...value.items, ...add])) });
    setSnap(null);
  };

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
      <Pressable testID="kitchen-snap" accessibilityRole="button" accessibilityLabel={t.kitchenSnap} onPress={snapKitchen} style={({ pressed }) => [styles.eatBanner, { marginTop: 12 }, pressed && styles.pressed]}>
        <View style={styles.bannerIcon}>
          <AppIcon name="camera.fill" color={colors.onBrandPrimary} size={23} />
        </View>
        <View style={styles.flex}>
          <Text style={styles.bannerTitle}>{t.kitchenSnap}</Text>
          <Text style={styles.bannerSub}>{t.kitchenSnapSub}</Text>
        </View>
      </Pressable>
      {snap ? (
        <View style={styles.reasonCard} testID="kitchen-snap-panel">
          {snap.phase === "reading" ? (
            <View testID="kitchen-snap-reading">
              <ActivityIndicator color={colors.brandPrimary} />
              <Text style={styles.reasonText}>{t.kitchenSnapReading}</Text>
            </View>
          ) : null}
          {snap.phase === "error" ? (
            <View>
              <Text style={styles.reasonText} testID="kitchen-snap-error">
                {snap.message}
              </Text>
              <Pressable testID="kitchen-snap-dismiss" accessibilityRole="button" onPress={() => setSnap(null)} style={styles.linkButton}>
                <Text style={styles.linkText}>{t.kitchenSnapCancel}</Text>
              </Pressable>
            </View>
          ) : null}
          {snap.phase === "review" ? (
            <View testID="kitchen-snap-review">
              <Text style={styles.reasonText}>{snap.found.length ? t.kitchenSnapFound : t.kitchenSnapNone}</Text>
              {snap.found.length ? (
                <View style={styles.chipWrap}>
                  {snap.found.map((item) => (
                    <Chip key={item.id} label={`snap-${item.id}`} text={label(item)} selected={!!snap.keep[item.id]} onPress={() => setSnap({ ...snap, keep: { ...snap.keep, [item.id]: !snap.keep[item.id] } })} />
                  ))}
                </View>
              ) : null}
              {snap.unmatched.length ? (
                <Text style={styles.mutedText} testID="kitchen-snap-unmatched">
                  {t.kitchenSnapNotMatched} {snap.unmatched.join(", ")}
                </Text>
              ) : null}
              <View style={[styles.row, { marginTop: 10, alignItems: "center", columnGap: 18 }]}>
                {snap.found.length ? (
                  <Pressable testID="kitchen-snap-add" accessibilityRole="button" onPress={addSnapped} style={styles.linkButton}>
                    <Text style={styles.linkText}>{t.kitchenSnapAdd}</Text>
                  </Pressable>
                ) : null}
                <Pressable testID="kitchen-snap-cancel" accessibilityRole="button" onPress={() => setSnap(null)} style={styles.linkButton}>
                  <Text style={styles.mutedText}>{t.kitchenSnapCancel}</Text>
                </Pressable>
              </View>
            </View>
          ) : null}
        </View>
      ) : null}
      {ingredients && !searching ? (
        <View style={[styles.chipWrap, { marginTop: 12 }]} testID="kitchen-tabs">
          <Chip label="tab-all" text={t.kitchenAllTab} selected={tab === "all"} onPress={() => setTab("all")} />
          {GROUPS.filter((group) => ingredients.some((item) => item.group === group.id)).map((group) => (
            <Chip key={group.id} label={`tab-${group.id}`} text={t[group.label] as string} selected={tab === group.id} onPress={() => setTab(group.id)} />
          ))}
        </View>
      ) : null}
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
        ? GROUPS.filter((group) => tab === "all" || group.id === tab).map((group) => {
            const members = ingredients.filter((item) => item.group === group.id);
            if (!members.length) return null;
            const picked = members.filter((item) => chosen.has(item.id)).length;
            const open = tab !== "all" || !closed[group.id];
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
