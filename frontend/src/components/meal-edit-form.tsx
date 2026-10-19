import { useState } from "react";
import { Text, View } from "react-native";

import { Button, Field } from "@/src/components/ui";
import type { Copy } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import type { LoggedMeal } from "@/src/types";

export type MealChanges = { name: string; calories: number; protein_g: number; carbs_g: number; fat_g: number };

// Inline editor for one logged meal; Save sends only a PATCH /meals/{id} body, the parent does the request.
export function MealEditForm({ meal, t, busy, onSave, onCancel }: { meal: LoggedMeal; t: Copy; busy: boolean; onSave: (changes: MealChanges) => void; onCancel: () => void }) {
  const styles = useStyles();
  const [name, setName] = useState(meal.name);
  const [calories, setCalories] = useState(String(meal.calories));
  const [protein, setProtein] = useState(String(meal.protein_g));
  const [carbs, setCarbs] = useState(String(meal.carbs_g));
  const [fat, setFat] = useState(String(meal.fat_g));
  const [error, setError] = useState("");

  const save = () => {
    const changes = { name: name.trim(), calories: Math.round(Number(calories)), protein_g: Number(protein), carbs_g: Number(carbs), fat_g: Number(fat) };
    const numbers = [changes.calories, changes.protein_g, changes.carbs_g, changes.fat_g];
    if (!changes.name || numbers.some((value) => !Number.isFinite(value) || value < 0)) {
      setError(t.checkNumbers);
      return;
    }
    setError("");
    onSave(changes);
  };

  return (
    <View style={styles.editForm} testID={`edit-meal-form-${meal.id}`}>
      <Field label={t.mealNameLabel} value={name} onChangeText={setName} />
      <Field label={t.caloriesLabel} value={calories} onChangeText={setCalories} keyboardType="numeric" />
      <Field label={t.proteinLabel} value={protein} onChangeText={setProtein} keyboardType="numeric" />
      <Field label={t.carbsLabel} value={carbs} onChangeText={setCarbs} keyboardType="numeric" />
      <Field label={t.fatLabel} value={fat} onChangeText={setFat} keyboardType="numeric" />
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      <View style={styles.row}>
        <View style={styles.half}>
          <Button testID={`edit-meal-save-${meal.id}`} label={t.save} onPress={save} disabled={busy} />
        </View>
        <View style={styles.half}>
          <Button testID={`edit-meal-cancel-${meal.id}`} label={t.cancel} onPress={onCancel} secondary disabled={busy} />
        </View>
      </View>
    </View>
  );
}
