import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, useWindowDimensions, View } from "react-native";

import { Button, Chip } from "@/src/components/ui";
import { useAuth } from "@/src/context/auth";
import { formatQuantity, MEAL_SLOTS, maxQuantity, portionText, scaledNutrition } from "@/src/lib/food";
import { mealTypeLabel } from "@/src/i18n";
import { useStyles } from "@/src/styles";
import type { FoodItem } from "@/src/types";

export type SheetChoice = { mealType: string; factor: number; quantity: number; label: string };

const STEP = 0.5;

// A compact bottom sheet to pick the serving, how many, and the meal slot, with the totals updating as you go.
export function FoodSheet({ food, initialSlot, busy, onAdd, onClose }: { food: FoodItem | null; initialSlot: string; busy: boolean; onAdd: (food: FoodItem, choice: SheetChoice) => void; onClose: () => void }) {
  const styles = useStyles();
  const { t } = useAuth();
  return (
    <Modal visible={food !== null} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.sheetBackdrop} onPress={onClose} accessibilityLabel={t.close} testID="food-sheet-backdrop">
        {/* A press on the sheet itself must not close it. */}
        <Pressable style={{ width: "100%", alignItems: "center" }} onPress={() => undefined} accessible={false}>
          {food ? <SheetBody key={food.id} food={food} initialSlot={initialSlot} busy={busy} onAdd={onAdd} onClose={onClose} /> : null}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function SheetBody({ food, initialSlot, busy, onAdd, onClose }: { food: FoodItem; initialSlot: string; busy: boolean; onAdd: (food: FoodItem, choice: SheetChoice) => void; onClose: () => void }) {
  const styles = useStyles();
  const { lang, t } = useAuth();
  const [optionIndex, setOptionIndex] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [mealType, setMealType] = useState(initialSlot);
  const { height } = useWindowDimensions();

  const option = food.servings[optionIndex] ?? { label: food.serving, factor: 1 };
  const limit = maxQuantity(food, option.factor);
  const safeQuantity = Math.min(quantity, limit);
  const total = scaledNutrition(food, option.factor * safeQuantity);
  const title = lang === "te" && food.te ? food.te : food.name;

  return (
    <View style={[styles.sheet, { maxHeight: Math.round(height * 0.92) }]} testID="food-sheet">
      <View style={styles.sheetHandle} />
      <ScrollView style={{ flexGrow: 0 }} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <Text style={styles.sheetTitle} testID="food-sheet-name">
          {title}
        </Text>
        {lang === "te" && food.te ? <Text style={styles.mutedText}>{food.name}</Text> : null}

        <Text style={styles.fieldLabel}>{t.servingLabel}</Text>
        <View style={styles.chipWrap}>
          {food.servings.map((item, index) => (
            <Chip key={item.label} label={item.label} selected={index === optionIndex} onPress={() => setOptionIndex(index)} />
          ))}
        </View>

        <Text style={styles.fieldLabel}>{t.quantityLabel}</Text>
        <View style={styles.stepperRow}>
          <Pressable testID="food-qty-minus" accessibilityRole="button" accessibilityLabel="−" disabled={safeQuantity <= STEP} onPress={() => setQuantity(Math.max(STEP, safeQuantity - STEP))} style={[styles.stepperButton, safeQuantity <= STEP && styles.disabled]}>
            <Text style={styles.stepperButtonText}>−</Text>
          </Pressable>
          <Text style={styles.stepperValue} testID="food-qty-value">
            {formatQuantity(safeQuantity)}
          </Text>
          <Pressable testID="food-qty-plus" accessibilityRole="button" accessibilityLabel="+" disabled={safeQuantity >= limit} onPress={() => setQuantity(Math.min(limit, safeQuantity + STEP))} style={[styles.stepperButton, safeQuantity >= limit && styles.disabled]}>
            <Text style={styles.stepperButtonText}>+</Text>
          </Pressable>
        </View>

        <Text style={styles.fieldLabel}>{t.mealType}</Text>
        <View style={styles.chipWrap}>
          {MEAL_SLOTS.map((slot) => (
            <Chip key={slot} label={slot} text={mealTypeLabel(t, slot)} selected={mealType === slot} onPress={() => setMealType(slot)} />
          ))}
        </View>

        <View style={styles.totalsRow} testID="food-sheet-totals">
          <Text style={styles.totalKcal} testID="food-sheet-kcal">
            {total.calories} kcal
          </Text>
          <Text style={styles.totalMacro}>
            {total.protein_g}g {t.proteinWord}
          </Text>
          <Text style={styles.totalMacro}>
            {total.carbs_g}g {t.carbsWord}
          </Text>
          <Text style={styles.totalMacro}>
            {total.fat_g}g {t.fatWord}
          </Text>
        </View>
        <Button testID="food-sheet-add" label={busy ? "..." : `${t.addToLog} · ${portionText(option.label, safeQuantity)}`} disabled={busy} onPress={() => onAdd(food, { mealType, factor: option.factor, quantity: safeQuantity, label: option.label })} />
        <Button testID="food-sheet-cancel" label={t.cancel} secondary onPress={onClose} />
        {food.estimate ? <Text style={styles.disclaimer}>{t.estimateNote}</Text> : null}
      </ScrollView>
    </View>
  );
}
