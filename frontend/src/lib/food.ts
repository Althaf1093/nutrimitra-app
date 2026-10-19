import type { FoodItem } from "@/src/types";

export const MEAL_SLOTS = ["breakfast", "lunch", "snack", "dinner"];

// The server rejects a single meal above these, so the quantity stepper stops before them.
const MAX_CALORIES = 3000;
const MAX_QUANTITY = 20;

/** Which meal slot to suggest at this hour: breakfast until 11, lunch until 15, a snack until 18, then dinner. */
export function defaultSlot(date: Date = new Date()): string {
  const hour = date.getHours();
  if (hour >= 5 && hour < 11) return "breakfast";
  if (hour >= 11 && hour < 15) return "lunch";
  if (hour >= 15 && hour < 18) return "snack";
  return "dinner";
}

const oneDecimal = (value: number) => Math.round(value * 10) / 10;

/** The food's nutrition for a serving that is `factor` times its default. */
export function scaledNutrition(food: FoodItem, factor: number) {
  return {
    calories: Math.round(food.calories * factor),
    protein_g: oneDecimal(food.protein_g * factor),
    carbs_g: oneDecimal(food.carbs_g * factor),
    fat_g: oneDecimal(food.fat_g * factor),
  };
}

/** The largest quantity (in steps of 0.5) the server will accept for this serving. */
export function maxQuantity(food: FoodItem, factor: number): number {
  const perOne = Math.max(1, food.calories * factor);
  return Math.max(0.5, Math.min(MAX_QUANTITY, Math.floor((MAX_CALORIES / perOne) * 2) / 2));
}

export const formatQuantity = (quantity: number) => (Number.isInteger(quantity) ? String(quantity) : quantity.toFixed(1));

/** "1 bowl (150 g)", or "2 × 1 bowl (150 g)" for a bigger helping. */
export const portionText = (label: string, quantity: number) => (quantity === 1 ? label : `${formatQuantity(quantity)} × ${label}`);

/** The POST /meals body for adding this food. */
export function foodMealBody(food: FoodItem, mealType: string, factor = 1, quantity = 1, label = food.serving) {
  return { meal_type: mealType, name: food.name, ...scaledNutrition(food, factor * quantity), source: "food search", portion: portionText(label, quantity) };
}
