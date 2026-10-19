import { useState } from "react";
import { Text, View } from "react-native";

import { Button, Chip, Field } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { MEAL_SLOTS } from "@/src/lib/food";
import { mealTypeLabel } from "@/src/i18n";
import { useStyles } from "@/src/styles";

export type CustomFood = { meal_type: string; name: string; calories: number; protein_g: number; carbs_g: number; fat_g: number };

// The manual path of Log food: type a name and the numbers yourself. Protein, carbs and fat may stay empty.
export function CustomFoodForm({ initialName, initialSlot, busy, onAdd, onCancel }: { initialName: string; initialSlot: string; busy: boolean; onAdd: (food: CustomFood) => void; onCancel: () => void }) {
  const styles = useStyles();
  const { t } = useAuth();
  const [name, setName] = useState(initialName);
  const [calories, setCalories] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [mealType, setMealType] = useState(initialSlot);
  const [error, setError] = useState("");

  const submit = () => {
    const food = { meal_type: mealType, name: name.trim(), calories: Math.round(Number(calories)), protein_g: Number(protein || 0), carbs_g: Number(carbs || 0), fat_g: Number(fat || 0) };
    const numbers = [food.calories, food.protein_g, food.carbs_g, food.fat_g];
    if (!food.name || !calories.trim() || numbers.some((value) => !Number.isFinite(value) || value < 0)) {
      setError(t.checkNumbers);
      return;
    }
    setError("");
    onAdd(food);
  };

  return (
    <View testID="custom-food-form">
      <Text style={styles.sectionTitleSmall}>{t.addCustomTitle}</Text>
      <Field label={t.mealNameLabel} value={name} onChangeText={setName} />
      <Field label={t.caloriesLabel} value={calories} onChangeText={setCalories} keyboardType="numeric" />
      <Field label={t.proteinLabel} value={protein} onChangeText={setProtein} keyboardType="numeric" />
      <Field label={t.carbsLabel} value={carbs} onChangeText={setCarbs} keyboardType="numeric" />
      <Field label={t.fatLabel} value={fat} onChangeText={setFat} keyboardType="numeric" />
      <Text style={styles.fieldLabel}>{t.mealType}</Text>
      <View style={styles.chipWrap}>
        {MEAL_SLOTS.map((slot) => (
          <Chip key={slot} label={slot} text={mealTypeLabel(t, slot)} selected={mealType === slot} onPress={() => setMealType(slot)} />
        ))}
      </View>
      {error ? (
        <Text style={styles.errorText} testID="custom-food-error">
          {error}
        </Text>
      ) : null}
      <Button testID="custom-food-add" label={busy ? "..." : t.addToLog} onPress={submit} disabled={busy} />
      <Button testID="custom-food-cancel" label={t.backToSearch} onPress={onCancel} secondary />
    </View>
  );
}
