import { ModalShell } from "@/src/components/modal-shell";
import { Redirect, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from "react-native";

import { api, del, post } from "@/src/api";
import { CustomFoodForm, type CustomFood } from "@/src/components/custom-food-form";
import { FoodSheet, type SheetChoice } from "@/src/components/food-sheet";
import { PhotoLogger } from "@/src/components/photo-logger";
import { ToastProvider, useToast } from "@/src/components/toast";
import { AppIcon, Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { defaultSlot, foodMealBody, MEAL_SLOTS } from "@/src/lib/food";
import { mealTypeLabel, type Copy } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import { useTheme } from "@/src/theme";
import type { FoodItem, LoggedMeal } from "@/src/types";

type Mode = "search" | "photo" | "custom";

const DEBOUNCE_MS = 200;
const ADDED_MS = 1500;
// Quick category chips: the label key, and the search each one runs (the catalogue is searched in English).
const CATEGORIES: { key: keyof Copy; id: string; query: string }[] = [
  { key: "catEggs", id: "eggs", query: "egg" },
  { key: "catDosa", id: "dosa", query: "dosa" },
  { key: "catIdli", id: "idli", query: "idli" },
  { key: "catRice", id: "rice", query: "rice" },
  { key: "catDal", id: "dal", query: "dal" },
  { key: "catCurry", id: "curry", query: "curry" },
  { key: "catSnacks", id: "snacks", query: "snacks" },
  { key: "catFruits", id: "fruits", query: "fruits" },
  { key: "catDrinks", id: "drinks", query: "drinks" },
];

async function fetchHome() {
  const [recents, frequents] = await Promise.all([api<{ results: FoodItem[] }>("/foods/recent?limit=8"), api<{ results: FoodItem[] }>("/foods/frequent?limit=8")]);
  const history = recents.results.length > 0 || frequents.results.length > 0;
  const popular = history ? [] : (await api<{ results: FoodItem[] }>("/foods/search?q=&limit=10")).results;
  return { recent: recents.results, frequent: frequents.results, popular };
}

export default function LogFoodScreen() {
  // Its own toast host: on a phone a modal screen covers the app's main one.
  return (
    <ToastProvider bottom={24}>
      <LogFood />
    </ToastProvider>
  );
}

function LogFood() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const params = useLocalSearchParams<{ mode?: string; slot?: string }>();
  const { lang, t, status } = useAuth();
  const [mode, setMode] = useState<Mode>(params.mode === "photo" ? "photo" : "search");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FoodItem[]>([]);
  const [searched, setSearched] = useState("");
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState<FoodItem[]>([]);
  const [frequent, setFrequent] = useState<FoodItem[]>([]);
  const [popular, setPopular] = useState<FoodItem[]>([]);
  const [sheetFood, setSheetFood] = useState<FoodItem | null>(null);
  const [busy, setBusy] = useState(false);
  const [added, setAdded] = useState<Record<string, boolean>>({});
  const [customName, setCustomName] = useState("");
  const [snapped, setSnapped] = useState(false);
  // "I ate something else" opens this screen for one meal slot; otherwise the slot follows the time of day.
  const currentSlot = () => (params.slot && MEAL_SLOTS.includes(params.slot) ? params.slot : defaultSlot());
  const requestId = useRef(0);
  const adding = useRef(false);
  const failedText = t.searchFailed;

  // Recent and frequent foods for the empty box; common foods when there is no history yet.
  const refreshHome = useCallback(() => {
    fetchHome()
      .then((home) => {
        setRecent(home.recent);
        setFrequent(home.frequent);
        setPopular(home.popular);
      })
      .catch(() => undefined); // The sections are a convenience; searching still works.
  }, []);

  useEffect(() => {
    if (status === "ready") refreshHome();
  }, [status, refreshHome]);

  // Suggestions as you type, after a short pause. A newer keystroke makes an older answer irrelevant.
  useEffect(() => {
    const text = query.trim();
    const id = ++requestId.current;
    if (!text) return;
    const handle = setTimeout(async () => {
      try {
        const found = await api<{ results: FoodItem[] }>(`/foods/search?q=${encodeURIComponent(text)}&limit=30`);
        if (id !== requestId.current) return;
        setResults(found.results);
        setSearched(text);
      } catch {
        if (id === requestId.current) toast.show(failedText, { type: "error" });
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [query, toast, failedText]);

  // Typing clears or starts the "searching" state here, not in the effect, so the effect only talks to the server.
  const onQuery = (value: string) => {
    setQuery(value);
    if (value.trim()) {
      setLoading(true);
    } else {
      setResults([]);
      setSearched("");
      setLoading(false);
    }
  };

  const undo = useCallback(
    async (id: string) => {
      try {
        await del(`/meals/${id}`);
        toast.show(t.undone, { type: "info" });
      } catch {
        toast.show(t.couldNotUndo, { type: "error" });
      }
      refreshHome();
    },
    [toast, t, refreshHome],
  );

  // One request for every way of adding: a catalogue food, a sheet choice or a custom food.
  const logMeal = async (body: { meal_type: string; name: string; calories: number; protein_g: number; carbs_g: number; fat_g: number; fibre_g?: number; source: string; portion?: string }) => {
    try {
      const saved = await post<LoggedMeal>("/meals", body);
      toast.show(`${t.addMeal} · ${mealTypeLabel(t, body.meal_type)}`, { actionLabel: t.undo, onAction: () => undo(saved.id) });
      refreshHome();
      return true;
    } catch (err) {
      toast.show(err instanceof Error ? err.message : t.couldNotLogMeal, { type: "error" });
      return false;
    }
  };

  const quickAdd = async (food: FoodItem) => {
    if (adding.current) return;
    adding.current = true;
    const ok = await logMeal(foodMealBody(food, currentSlot()));
    adding.current = false;
    if (ok) {
      setAdded((current) => ({ ...current, [food.id]: true }));
      setTimeout(() => setAdded((current) => ({ ...current, [food.id]: false })), ADDED_MS);
    }
  };

  const addFromSheet = async (food: FoodItem, choice: SheetChoice) => {
    setBusy(true);
    const ok = await logMeal(foodMealBody(food, choice.mealType, choice.factor, choice.quantity, choice.label));
    setBusy(false);
    if (ok) setSheetFood(null);
  };

  const addCustom = async (food: CustomFood) => {
    setBusy(true);
    const ok = await logMeal({ ...food, source: "manual" });
    setBusy(false);
    if (ok) setMode("search");
  };

  const openCustom = () => {
    setCustomName(query.trim());
    setMode("custom");
  };

  // Route guard: this modal requires an authenticated, onboarded session.
  if (status === "loading") {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brandPrimary} />
      </View>
    );
  }
  if (status !== "ready") {
    return <Redirect href={status === "consent" ? "/consent" : status === "onboarding" ? "/onboarding" : "/welcome"} />;
  }

  const renderRow = (food: FoodItem) => {
    const done = added[food.id];
    const primary = lang === "te" && food.te ? food.te : food.name;
    return (
      // A View with two sibling buttons (open the sheet, quick add): a button cannot contain a button.
      <View key={food.id} testID={`food-row-${food.id}`} style={styles.foodRow}>
        <Pressable accessibilityRole="button" accessibilityLabel={primary} onPress={() => setSheetFood(food)} style={({ pressed }) => [styles.flex, pressed && styles.pressed]}>
          <Text style={styles.foodName}>{primary}</Text>
          <Text style={styles.foodMeta}>
            {lang === "te" && food.te ? `${food.name} · ` : ""}
            {food.serving} · {food.calories} kcal
          </Text>
        </Pressable>
        <Pressable testID={`food-add-${food.id}`} accessibilityRole="button" accessibilityLabel={`${t.addWord} ${primary}`} onPress={() => quickAdd(food)} style={[styles.foodAdd, done && styles.foodAddDone]}>
          <Text style={done ? styles.foodAddDoneText : styles.foodAddText}>{done ? "✓" : "+"}</Text>
        </Pressable>
      </View>
    );
  };

  const section = (title: string, items: FoodItem[], id: string) =>
    items.length ? (
      <View testID={id}>
        <Text style={[styles.sectionTitleSmall, { marginTop: 22, marginBottom: 2 }]}>{title}</Text>
        {items.map(renderRow)}
      </View>
    ) : null;

  const typing = query.trim().length > 0;
  const noMatch = typing && !loading && searched === query.trim() && results.length === 0;

  return (
    <ModalShell testID="log-food-screen">
      <View style={styles.appHeader}>
        <View style={styles.flex}>
          <Text style={styles.eyebrow}>{t.logFoodEyebrow.toUpperCase()}</Text>
          <Text style={styles.headerTitle}>{mode === "photo" ? t.snapMeal : t.logFood}</Text>
        </View>
        <Pressable testID="log-food-close" accessibilityRole="button" accessibilityLabel={t.close} onPress={() => router.back()} style={styles.iconButton}>
          <AppIcon name="xmark" color={colors.onSurface} size={20} />
        </Pressable>
      </View>
      <ScrollView contentContainerStyle={styles.screenContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        {mode === "photo" ? <PhotoLogger initialSlot={currentSlot()} autoStart={params.mode === "photo" || snapped} onLogged={() => router.back()} onBack={() => setMode("search")} /> : null}
        {mode === "custom" ? <CustomFoodForm key={customName} initialName={customName} initialSlot={currentSlot()} busy={busy} onAdd={addCustom} onCancel={() => setMode("search")} /> : null}
        {mode === "search" ? (
          <View>
            <Pressable
              testID="photo-mode-button"
              accessibilityRole="button"
              accessibilityLabel={t.snapMeal}
              onPress={() => {
                setSnapped(true);
                setMode("photo");
              }}
              style={({ pressed }) => [styles.eatBanner, { marginTop: 0, marginBottom: 14 }, pressed && styles.pressed]}
            >
              <View style={styles.bannerIcon}>
                <AppIcon name="camera.fill" color={colors.onBrandPrimary} size={23} />
              </View>
              <View style={styles.flex}>
                <Text style={styles.bannerTitle}>{t.snapMeal}</Text>
                <Text style={styles.bannerSub}>{t.snapMealSub}</Text>
              </View>
            </Pressable>
            <View style={styles.searchBar}>
              <TextInput
                testID="food-search-input"
                accessibilityLabel={t.searchFoods}
                autoFocus
                value={query}
                onChangeText={onQuery}
                placeholder={t.searchFoodPlaceholder}
                placeholderTextColor={colors.muted}
                autoCorrect={false}
                autoCapitalize="none"
                returnKeyType="search"
                style={styles.searchInput}
              />
              {loading ? <ActivityIndicator size="small" color={colors.brandPrimary} testID="food-search-loading" /> : null}
              {query ? (
                <Pressable testID="food-search-clear" accessibilityRole="button" accessibilityLabel={t.clearSearch} onPress={() => onQuery("")} style={styles.searchClear}>
                  <Text style={styles.searchClearText}>✕</Text>
                </Pressable>
              ) : null}
            </View>

            {typing ? (
              <View testID="food-results">
                {results.map(renderRow)}
                {noMatch ? (
                  <View style={styles.reasonCard} testID="food-no-match">
                    <Text style={styles.reasonText}>{t.noMatchAddYourself}</Text>
                  </View>
                ) : null}
              </View>
            ) : (
              <View>
                <Text style={[styles.fieldLabel, { marginTop: 18 }]}>{t.browseFoods}</Text>
                <View style={styles.categoryRow} testID="food-categories">
                  {CATEGORIES.map((category) => (
                    <Chip key={category.id} label={category.id} text={t[category.key] as string} selected={false} onPress={() => onQuery(category.query)} />
                  ))}
                </View>
                {section(t.recentFoods, recent, "food-recent")}
                {section(t.frequentFoods, frequent, "food-frequent")}
                {section(t.popularFoods, popular, "food-popular")}
              </View>
            )}

            <Pressable testID="food-add-custom-link" accessibilityRole="button" onPress={openCustom} style={[styles.linkButton, { marginTop: 14 }]}>
              <Text style={styles.linkText}>{t.addCustomFood}</Text>
            </Pressable>
            <Text style={styles.disclaimer}>{t.estimateNote}</Text>
          </View>
        ) : null}
      </ScrollView>
      <FoodSheet food={sheetFood} initialSlot={currentSlot()} busy={busy} onAdd={addFromSheet} onClose={() => setSheetFood(null)} />
    </ModalShell>
  );
}
