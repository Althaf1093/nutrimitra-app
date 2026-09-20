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

export type Plan = { days: PlanDay[]; reasoning: string; goal: string };

export type Dashboard = {
  date: string;
  meals: Record<string, unknown>[];
  activities: Record<string, unknown>[];
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
