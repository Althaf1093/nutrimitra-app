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

// An ingredient a planned meal uses, and whether the person has it at home.
export type IngredientRef = { id: string; name: string; te: string; group: string; have: boolean };

export type Meal = {
  type: string;
  name: string;
  te?: string;
  uses?: IngredientRef[];
  minutes?: number;
  // Something else was logged in this meal's slot today.
  ate_other?: boolean;
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
export type Plan = {
  days: PlanDay[];
  reasoning: string;
  goal: string;
  today_index?: number;
  ai_status?: string;
  ai_message?: string;
  // Built from the person's kitchen; what to buy; and whether the kitchen changed since the plan was made.
  kitchen_based?: boolean;
  also_buy?: IngredientRef[];
  kitchen_changed?: boolean;
};

export type ShoppingItem = IngredientRef & { meals: number };
export type ShoppingList = { kitchen_based: boolean; household_size: number; to_buy: ShoppingItem[]; have: ShoppingItem[]; kitchen_changed: boolean };

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
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  target_protein_g: number;
  target_carbs_g: number;
  target_fat_g: number;
  water_ml: number;
  target_water_ml: number;
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

// An ingredient from GET /kitchen/ingredients: names in both languages, its group, and its diet level.
export type Ingredient = {
  id: string;
  name: string;
  te: string;
  group: string;
  diet: "vegan" | "veg" | "egg" | "non";
  aliases: string[];
  protein: boolean;
  assumed: boolean;
};

export type KitchenSnapResult = { matches: Ingredient[]; unmatched: string[] };

export type Kitchen = { items: string[]; meals_per_day: number; household_size: number; cooking_time: string | null; updated_at?: string };

export type CheckinStatus = "nothing_logged" | "low_protein" | "on_track" | "low_energy" | "above";
export type CheckinResult = { date: string; status: CheckinStatus; calories: number; target_calories: number; protein_g: number; target_protein_g: number; adjusted_day: number | null };
