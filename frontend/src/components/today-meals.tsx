import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import {
  MealEditForm,
  type MealChanges,
} from "@/src/components/meal-edit-form";
import { AppIcon, Button, MealCard } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { mealTypeLabel } from "@/src/i18n";
import { MEAL_SLOTS } from "@/src/lib/food";
import { useStyles } from "@/src/styles";
import { makeStyles, radius, useTheme } from "@/src/theme";
import type { LoggedMeal, Meal } from "@/src/types";

type Props = {
  wide?: boolean;
  logged: LoggedMeal[];
  suggestions: Meal[];
  busy: boolean;
  editingId: string | null;
  setEditingId: (id: string | null) => void;
  onSave: (id: string, changes: MealChanges) => void;
  onRemove: (item: LoggedMeal) => void;
  onAdd: (slot: string, mode?: "photo") => void;
  onLogSuggestion: (meal: Meal) => void;
  onSwap: (meal: Meal) => void;
};

const useSlot = makeStyles((colors) => ({
  tile: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  title: { flex: 1, color: colors.onCard, fontSize: 16, fontWeight: "700" },
  kcal: {
    color: colors.muted,
    fontSize: 14,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 4 },
  primary: {
    flexGrow: 1,
    flexBasis: 140,
    minHeight: 46,
    borderRadius: radius.pill,
    backgroundColor: colors.brandPrimary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 10,
  },
  primaryText: {
    color: colors.onBrandPrimary,
    fontSize: 14,
    fontWeight: "700",
  },
  outline: {
    flexGrow: 1,
    flexBasis: 140,
    minHeight: 46,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    borderColor: colors.brandPrimary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 10,
  },
  outlineText: { color: colors.brandPrimary, fontSize: 14, fontWeight: "700" },
  suggest: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: 10,
    minHeight: 32,
  },
  suggestText: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: "700",
    flexShrink: 1,
  },
}));

// Each meal has its own icon and colour, as in the design: breakfast saffron, lunch green, snack coral, dinner violet.
function slotTone(colors: ReturnType<typeof useTheme>["colors"], slot: string) {
  if (slot === "breakfast")
    return { icon: "breakfast", bg: colors.accentSoft, fg: colors.accent };
  if (slot === "lunch")
    return { icon: "lunch", bg: colors.brandSoft, fg: colors.brandPrimary };
  if (slot === "snack")
    return { icon: "snack", bg: colors.macroFatSoft, fg: colors.macroFat };
  return { icon: "dinner", bg: colors.macroFibreSoft, fg: colors.macroFibre };
}

// Today's food: only what the person logged, by meal slot. The plan's meal for a slot is a suggestion behind a small link.
export function TodayMeals({
  wide,
  logged,
  suggestions,
  busy,
  editingId,
  setEditingId,
  onSave,
  onRemove,
  onAdd,
  onLogSuggestion,
  onSwap,
}: Props) {
  const styles = useStyles();
  const slotStyles = useSlot();
  const { colors } = useTheme();
  const { t } = useAuth();
  const [open, setOpen] = useState<Record<string, boolean>>({});

  return (
    <View
      testID="today-meals"
      style={
        wide ? { flexDirection: "row", flexWrap: "wrap", gap: 16 } : undefined
      }
    >
      {logged.length === 0 ? (
        <View
          style={[styles.reasonCard, wide && { width: "100%", marginTop: 0 }]}
          testID="today-empty"
        >
          <Text style={styles.reasonText}>{t.nothingLoggedYet}</Text>
        </View>
      ) : null}
      {MEAL_SLOTS.map((slot) => {
        const items = logged.filter((item) => item.meal_type === slot);
        const suggestion = suggestions.find((meal) => meal.type === slot);
        const label = mealTypeLabel(t, slot);
        const tone = slotTone(colors, slot);
        const kcal = items.reduce((sum, item) => sum + item.calories, 0);
        return (
          <View
            key={slot}
            style={[
              styles.reasonCard,
              wide && { width: "48.5%", marginTop: 0 },
            ]}
            testID={`slot-${slot}`}
          >
            <View
              style={{ flexDirection: "row", alignItems: "center", gap: 12 }}
            >
              <View style={[slotStyles.tile, { backgroundColor: tone.bg }]}>
                <AppIcon name={tone.icon} color={tone.fg} size={22} />
              </View>
              <Text style={slotStyles.title} accessibilityRole="header">
                {label}
              </Text>
              {items.length ? (
                <Text style={slotStyles.kcal} testID={`slot-kcal-${slot}`}>
                  {kcal} kcal
                </Text>
              ) : null}
            </View>
            {items.map((item) =>
              editingId === item.id ? (
                <MealEditForm
                  key={item.id}
                  meal={item}
                  t={t}
                  busy={busy}
                  onSave={(changes) => onSave(item.id, changes)}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <View
                  key={item.id}
                  style={styles.logRow}
                  testID={`logged-meal-${item.id}`}
                >
                  <View style={styles.flex}>
                    <Text style={styles.mealName}>{item.name}</Text>
                    <Text style={styles.mealMeta}>
                      {item.portion ? `${item.portion} · ` : ""}
                      {item.calories} kcal · {item.protein_g}g {t.proteinWord}
                    </Text>
                  </View>
                  <View style={styles.rowActions}>
                    <Pressable
                      testID={`edit-meal-${item.id}`}
                      accessibilityRole="button"
                      accessibilityLabel={`${t.edit} ${item.name}`}
                      disabled={busy}
                      onPress={() => setEditingId(item.id)}
                      style={({ pressed }) => [
                        styles.removeButton,
                        pressed && styles.pressed,
                        busy && styles.disabled,
                      ]}
                    >
                      <Text style={styles.linkText}>{t.edit}</Text>
                    </Pressable>
                    <Pressable
                      testID={`remove-meal-${item.id}`}
                      accessibilityRole="button"
                      accessibilityLabel={`${t.remove} ${item.name}`}
                      disabled={busy}
                      onPress={() => onRemove(item)}
                      style={({ pressed }) => [
                        styles.removeButton,
                        pressed && styles.pressed,
                        busy && styles.disabled,
                      ]}
                    >
                      <Text style={styles.linkText}>{t.remove}</Text>
                    </Pressable>
                  </View>
                </View>
              ),
            )}
            <View style={slotStyles.actions}>
              <Pressable
                testID={`add-food-${slot}`}
                accessibilityRole="button"
                accessibilityLabel={`${t.addFood} (${label})`}
                onPress={() => onAdd(slot)}
                style={({ pressed }) => [
                  slotStyles.primary,
                  pressed && styles.pressed,
                ]}
              >
                <AppIcon name="add" color={colors.onBrandPrimary} size={18} />
                <Text style={slotStyles.primaryText}>{t.addFood}</Text>
              </Pressable>
              <Pressable
                testID={`snap-meal-${slot}`}
                accessibilityRole="button"
                accessibilityLabel={`${t.snapMeal} (${label})`}
                onPress={() => onAdd(slot, "photo")}
                style={({ pressed }) => [
                  slotStyles.outline,
                  pressed && styles.pressed,
                ]}
              >
                <AppIcon name="camera" color={colors.brandPrimary} size={18} />
                <Text style={slotStyles.outlineText} numberOfLines={1}>
                  {t.snapMealShort}
                </Text>
              </Pressable>
            </View>
            {suggestion && !suggestion.logged ? (
              <Pressable
                testID={`suggestion-toggle-${slot}`}
                accessibilityRole="button"
                accessibilityState={{ expanded: !!open[slot] }}
                hitSlop={6}
                onPress={() =>
                  setOpen((current) => ({ ...current, [slot]: !current[slot] }))
                }
                style={slotStyles.suggest}
              >
                <AppIcon name="sparkles" color={colors.accent} size={16} />
                <Text style={slotStyles.suggestText}>
                  {t.suggestionFor.replace("{slot}", label.toLowerCase())}
                </Text>
                <AppIcon
                  name={open[slot] ? "up" : "down"}
                  color={colors.accent}
                  size={16}
                />
              </Pressable>
            ) : null}
            {suggestion && !suggestion.logged && open[slot] ? (
              <View style={{ marginTop: 8 }} testID={`suggestion-${slot}`}>
                <MealCard
                  meal={suggestion}
                  hideLog
                  onSwap={() => onSwap(suggestion)}
                  onAteOther={() => onAdd(slot)}
                />
                <Button
                  testID={`log-suggestion-${slot}`}
                  label={t.logThis}
                  onPress={() => onLogSuggestion(suggestion)}
                  secondary
                />
              </View>
            ) : null}
          </View>
        );
      })}
    </View>
  );
}
