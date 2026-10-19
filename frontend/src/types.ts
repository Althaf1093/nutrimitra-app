import type { Lang } from "@/src/i18n";

export type User = {
  id: string;
  email: string;
  name: string;
  onboarding_complete: boolean;
  language: Lang;
  // True until the person has agreed to the current Terms and Privacy Policy (asked once on next launch).
  needs_consent?: boolean;
  has_password?: boolean;
  // False until the person has entered the code emailed at sign-up. They can use the app meanwhile.
  email_verified?: boolean;
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
// ai_status is set when the AI could not build a fresh plan (e.g. "ai_busy"); the plan shown is the previous one or a fallback.
export type Plan = { days: PlanDay[]; reasoning: string; goal: string; today_index?: number; ai_status?: string; ai_message?: string };

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
  portion?: string;
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
  target_calories: number;
  activity_minutes: number;
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
  provider?: string;
};

export type ReminderPrefs = {
  meals: boolean;
  hydration: boolean;
  movement: boolean;
  weekly: boolean;
};

export type ServingOption = { label: string; factor: number };

// A row from GET /foods/search, /foods/recent or /foods/frequent. Values are per default serving and are estimates.
export type FoodItem = {
  id: string;
  name: string;
  te: string;
  category: string;
  serving: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  servings: ServingOption[];
  estimate: boolean;
  recent: boolean;
  times?: number;
};
