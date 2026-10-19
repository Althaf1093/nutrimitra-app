import type { Lang } from "@/src/i18n";

export type User = {
  id: string;
  email: string;
  name: string;
  onboarding_complete: boolean;
  language: Lang;
};

export type Profile = {
  age: number;
  sex: string;
  height_cm: number;
  weight_kg: number;
  target_weight_kg: number;
  dietary_preferences: string[];
  wellness_goal: string;
  language: Lang;
  [key: string]: unknown;
};

export type Meal = {
  type: string;
  name: string;
  portion: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  logged?: boolean;
};

export type PlanDay = { day: number; title: string; focus: string; meals: Meal[] };

// today_index: which day of the 7-day plan is "today" (days since the plan started, wrapped).
export type Plan = { days: PlanDay[]; reasoning: string; goal: string; today_index?: number };

export type LoggedMeal = {
  id: string;
  meal_type: string;
  name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  source: string;
  date: string;
};

export type LoggedActivity = {
  id: string;
  activity_type: string;
  duration_min: number;
  distance_km: number;
  active_calories: number;
  source: string;
  date: string;
};

export type Dashboard = {
  date: string;
  meals: LoggedMeal[];
  activities: LoggedActivity[];
  calories: number;
  active_calories: number;
  readiness: number;
  goal: string;
};

export type EatNow = {
  suggestion: Meal;
  target_calories: number;
  consumed_calories: number;
  remaining_calories: number;
  reasoning: string;
  disclaimer: string;
};

export type VisionResult = {
  name: string;
  portion: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  confidence: "low" | "medium" | "high";
  alternatives: string[];
  meal_type: string;
  model: string;
};

export type ReminderPrefs = {
  meals: boolean;
  hydration: boolean;
  movement: boolean;
  weekly: boolean;
};
