import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { MealEditForm, type MealChanges } from "@/src/components/meal-edit-form";
import { Button, MealCard } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { mealTypeLabel } from "@/src/i18n";
import { MEAL_SLOTS } from "@/src/lib/food";
import { useStyles } from "@/src/styles";
import type { LoggedMeal, Meal } from "@/src/types";

type Props = {
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

// Today's food: only what the person logged, by meal slot. The plan's meal for a slot is a suggestion behind a small link.
export function TodayMeals({ logged, suggestions, busy, editingId, setEditingId, onSave, onRemove, onAdd, onLogSuggestion, onSwap }: Props) {
  const styles = useStyles();
  const { t } = useAuth();
  const [open, setOpen] = useState<Record<string, boolean>>({});

  return (
    <View testID="today-meals">
      {logged.length === 0 ? (
        <View style={styles.reasonCard} testID="today-empty">
          <Text style={styles.reasonText}>{t.nothingLoggedYet}</Text>
        </View>
      ) : null}
      {MEAL_SLOTS.map((slot) => {
        const items = logged.filter((item) => item.meal_type === slot);
        const suggestion = suggestions.find((meal) => meal.type === slot);
        const label = mealTypeLabel(t, slot);
        const kcal = items.reduce((sum, item) => sum + item.calories, 0);
        return (
          <View key={slot} style={styles.reasonCard} testID={`slot-${slot}`}>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
              <Text style={styles.cardEyebrow}>{label.toUpperCase()}</Text>
              {items.length ? (
                <Text style={styles.mealMeta} testID={`slot-kcal-${slot}`}>
                  {kcal} kcal
                </Text>
              ) : null}
            </View>
            {items.map((item) =>
              editingId === item.id ? (
                <MealEditForm key={item.id} meal={item} t={t} busy={busy} onSave={(changes) => onSave(item.id, changes)} onCancel={() => setEditingId(null)} />
              ) : (
                <View key={item.id} style={styles.logRow} testID={`logged-meal-${item.id}`}>
                  <View style={styles.flex}>
                    <Text style={styles.mealName}>{item.name}</Text>
                    <Text style={styles.mealMeta}>
                      {item.portion ? `${item.portion} · ` : ""}
                      {item.calories} kcal · {item.protein_g}g {t.proteinWord}
                    </Text>
                  </View>
                  <View style={styles.rowActions}>
                    <Pressable testID={`edit-meal-${item.id}`} accessibilityRole="button" accessibilityLabel={`${t.edit} ${item.name}`} disabled={busy} onPress={() => setEditingId(item.id)} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed, busy && styles.disabled]}>
                      <Text style={styles.linkText}>{t.edit}</Text>
                    </Pressable>
                    <Pressable testID={`remove-meal-${item.id}`} accessibilityRole="button" accessibilityLabel={`${t.remove} ${item.name}`} disabled={busy} onPress={() => onRemove(item)} style={({ pressed }) => [styles.removeButton, pressed && styles.pressed, busy && styles.disabled]}>
                      <Text style={styles.linkText}>{t.remove}</Text>
                    </Pressable>
                  </View>
                </View>
              ),
            )}
            <View style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "center", columnGap: 18, marginTop: 6 }}>
              <Pressable testID={`add-food-${slot}`} accessibilityRole="button" accessibilityLabel={`${t.addFood} (${label})`} hitSlop={6} onPress={() => onAdd(slot)} style={styles.linkButton}>
                <Text style={styles.linkText}>+ {t.addFood}</Text>
              </Pressable>
              <Pressable testID={`snap-meal-${slot}`} accessibilityRole="button" accessibilityLabel={`${t.snapMeal} (${label})`} hitSlop={6} onPress={() => onAdd(slot, "photo")} style={styles.linkButton}>
                <Text style={styles.linkText}>{t.snapMeal}</Text>
              </Pressable>
              {suggestion && !suggestion.logged ? (
                <Pressable testID={`suggestion-toggle-${slot}`} accessibilityRole="button" accessibilityState={{ expanded: !!open[slot] }} hitSlop={6} onPress={() => setOpen((current) => ({ ...current, [slot]: !current[slot] }))} style={styles.linkButton}>
                  <Text style={styles.mutedText}>
                    {open[slot] ? "▾" : "▸"} {t.suggestionFor.replace("{slot}", label.toLowerCase())}
                  </Text>
                </Pressable>
              ) : null}
            </View>
            {suggestion && !suggestion.logged && open[slot] ? (
              <View style={{ marginTop: 8 }} testID={`suggestion-${slot}`}>
                <MealCard meal={suggestion} hideLog onSwap={() => onSwap(suggestion)} onAteOther={() => onAdd(slot)} />
                <Button testID={`log-suggestion-${slot}`} label={t.logThis} onPress={() => onLogSuggestion(suggestion)} secondary />
              </View>
            ) : null}
          </View>
        );
      })}
    </View>
  );
}
