import type { Meal, Plan } from "@/src/types";

/** What POST /meals takes for a meal that comes from the plan. */
export const planMealBody = (meal: Meal) => ({
  meal_type: meal.type,
  name: meal.name,
  calories: meal.calories,
  protein_g: meal.protein_g,
  carbs_g: meal.carbs_g,
  fat_g: meal.fat_g,
  ...(meal.fibre_g != null ? { fibre_g: meal.fibre_g } : {}),
  source: "plan",
});

/** A copy of the plan with one meal of one day flagged as logged (or not), so "+" turns into the check at once. */
export function markPlanMeal(plan: Plan, dayIndex: number, meal: Meal, logged: boolean): Plan {
  return {
    ...plan,
    days: plan.days.map((day, index) =>
      index === dayIndex ? { ...day, meals: day.meals.map((item) => (item.type === meal.type && item.name === meal.name ? { ...item, logged } : item)) } : day,
    ),
  };
}
