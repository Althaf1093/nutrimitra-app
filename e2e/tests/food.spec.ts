import type { Page } from "@playwright/test";

import { expect, test, type App } from "../fixtures";

// Log food: search suggestions, one-tap add, the serving sheet, custom food, recents, and the toast that goes away by itself.

const rows = (page: Page) => page.locator('[data-testid^="food-row-"]');

async function openLogFood(app: App) {
  await app.id("log-food-button").click();
  await expect(app.id("log-food-screen")).toBeVisible();
}

test("food: type egg, one-tap add, the toast leaves by itself, the meal is on Today", async ({ app }) => {
  await app.newUserOnToday("foodegg");
  await openLogFood(app);
  await expect(app.id("food-search-input")).toBeFocused();
  await app.shot("empty-box");

  await app.id("food-search-input").pressSequentially("egg", { delay: 40 });
  await expect(app.id("food-row-boiled-egg")).toBeVisible();
  for (const id of ["omelette", "scrambled-egg", "fried-egg-half-fry", "egg-curry"]) await expect(app.id(`food-row-${id}`)).toBeVisible();
  await expect(app.id("food-row-boiled-egg")).toContainText("1 large egg (50 g) · 78 kcal");
  await app.shot("egg-suggestions");

  const started = Date.now();
  await app.id("food-add-boiled-egg").click();
  await expect(app.id("toast-message")).toContainText("Meal logged");
  await expect(app.id("food-add-boiled-egg")).toContainText("✓");
  await app.shot("egg-added");

  // The toast: a small light pill, not a full-width black bar, and gone without a tap.
  const toast = app.id("toast");
  const box = (await toast.boundingBox())!;
  const viewport = app.page.viewportSize()!;
  expect(box.width).toBeLessThan(viewport.width - 24);
  const [red, green, blue] = (await toast.getByRole("button").first().evaluate((el) => getComputedStyle(el).backgroundColor)).match(/\d+/g)!.map(Number);
  expect((red + green + blue) / 3).toBeGreaterThan(200);
  await expect(toast).toHaveCount(0, { timeout: 8_000 });
  const shown = Date.now() - started;
  expect(shown).toBeGreaterThan(1_500);
  expect(shown).toBeLessThan(8_000);

  const meal = (await app.api("/dashboard")).body.meals[0];
  expect(meal).toMatchObject({ name: "Boiled egg", calories: 78, source: "food search", portion: "1 large egg (50 g)" });

  await app.id("log-food-close").click();
  await expect(app.id("today-screen")).toBeVisible();
  await expect(app.id("today-meals")).toContainText("Boiled egg");
  await expect(app.id("today-meals")).toContainText("78 kcal");
});

test("food: dosa shows many variants, the serving sheet scales the numbers", async ({ app }) => {
  await app.newUserOnToday("fooddosa");
  await openLogFood(app);
  await app.id("food-search-input").fill("dosa");
  await expect(app.id("food-row-masala-dosa")).toBeVisible();
  expect(await rows(app.page).count()).toBeGreaterThanOrEqual(8);
  for (const id of ["plain-dosa", "ragi-dosa", "karam-dosa", "rava-dosa", "pesarattu", "set-dosa", "onion-dosa"]) await expect(app.id(`food-row-${id}`)).toBeVisible();
  await app.shot("dosa-results");

  // A typo still finds them.
  await app.id("food-search-input").fill("dosaa");
  await expect(app.id("food-row-plain-dosa")).toBeVisible();

  await app.id("food-search-input").fill("masala dosa");
  await app.id("food-row-masala-dosa").click();
  await expect(app.id("food-sheet")).toBeVisible();
  await expect(app.id("food-sheet-kcal")).toHaveText("290 kcal");
  await app.id("food-qty-plus").click();
  await expect(app.id("food-qty-value")).toHaveText("1.5");
  await expect(app.id("food-sheet-kcal")).toHaveText("435 kcal");
  await app.id("chip-lunch").click();
  await app.shot("serving-sheet");
  await app.id("food-sheet-add").click();
  await expect(app.id("food-sheet")).toHaveCount(0);
  await expect(app.id("toast-message")).toContainText("Meal logged · Lunch");

  const meal = (await app.api("/dashboard")).body.meals[0];
  expect(meal).toMatchObject({ name: "Masala dosa", calories: 435, meal_type: "lunch", portion: "1.5 × 1 dosa with potato filling (200 g)" });
});

test("food: undo, recents and the empty-box sections", async ({ app }) => {
  await app.newUserOnToday("foodrecent");
  await openLogFood(app);
  await expect(app.id("food-categories")).toBeVisible();
  await expect(app.id("food-popular")).toBeVisible(); // no history yet: common foods
  for (const id of ["eggs", "dosa", "idli", "rice", "dal", "curry", "snacks", "fruits", "drinks"]) await expect(app.id(`chip-${id}`)).toBeVisible();

  // Undo removes what the one-tap add just logged.
  await app.id("chip-idli").click();
  await expect(app.id("food-search-input")).toHaveValue("idli");
  await app.id("food-add-idli").click();
  await app.id("toast-action").click();
  await expect(app.id("toast-message")).toHaveText("Undone");
  await expect.poll(async () => (await app.api("/dashboard")).body.meals.length).toBe(0);

  // Added again and kept: it is now a recent food.
  await app.id("food-add-idli").click();
  await expect.poll(async () => (await app.api("/dashboard")).body.meals.length).toBe(1);
  await app.id("food-search-clear").click();
  await expect(app.id("food-recent")).toBeVisible();
  await expect(app.id("food-recent")).toContainText("Idli");
  await app.shot("recent");
});

test("food: no match leads to a custom food, which is saved", async ({ app }) => {
  await app.newUserOnToday("foodcustom");
  await openLogFood(app);
  await app.id("food-search-input").fill("zzqxw granny special");
  await expect(app.id("food-no-match")).toContainText("No match. Add it yourself.");
  await app.shot("no-match");
  await app.id("food-add-custom-link").click();
  await expect(app.id("custom-food-form")).toBeVisible();
  await expect(app.id("field-meal-name")).toHaveValue("zzqxw granny special");

  // Name and calories are required.
  await app.id("custom-food-add").click();
  await expect(app.id("custom-food-error")).toBeVisible();

  await app.id("field-calories-(kcal)").fill("250");
  await app.id("field-protein-(g)").fill("9");
  await app.id("custom-food-add").click();
  await expect(app.id("toast-message")).toContainText("Meal logged");
  await expect(app.id("food-search-input")).toBeVisible(); // back to search
  const meal = (await app.api("/dashboard")).body.meals[0];
  expect(meal).toMatchObject({ name: "zzqxw granny special", calories: 250, protein_g: 9, source: "manual" });

  // It is now one of the recent foods, with the numbers that were typed.
  await app.id("food-search-clear").click();
  await expect(app.id("food-recent")).toContainText("zzqxw granny special");
  await expect(app.id("food-recent")).toContainText("250 kcal");
});

test("food: a failed search keeps the typed text and shows an error toast", async ({ app }) => {
  app.allow(/requestfailed .*\/foods\/search/, /console\.error Failed to load resource/, /console\.error \[Wellstride\] Could not reach the backend/);
  await app.newUserOnToday("foodfail");
  await openLogFood(app);
  await app.page.route("**/api/foods/search**", (route) => (route.request().url().includes("q=egg") ? route.abort("failed") : route.continue()));
  await app.id("food-search-input").fill("egg");
  await expect(app.id("toast")).toHaveAttribute("role", "alert");
  await expect(app.id("toast-message")).toContainText("Couldn't search right now");
  await expect(app.id("food-search-input")).toHaveValue("egg");
  await app.shot("search-failed");
});

test("food: the meal slot follows the time of day", async ({ app }) => {
  await app.page.clock.setFixedTime(new Date("2026-10-20T08:15:00"));
  await app.newUserOnToday("foodslot");
  await openLogFood(app);
  await app.id("food-search-input").fill("banana");
  await app.id("food-add-banana").click();
  await expect(app.id("toast-message")).toContainText("Breakfast");
  await app.page.clock.setFixedTime(new Date("2026-10-20T13:00:00"));
  await app.id("food-add-banana").click();
  await expect(app.id("toast-message")).toContainText("Lunch");
  await app.page.clock.setFixedTime(new Date("2026-10-20T16:30:00"));
  await app.id("food-add-banana").click();
  await expect(app.id("toast-message")).toContainText("Snack");
  await app.page.clock.setFixedTime(new Date("2026-10-20T21:00:00"));
  await app.id("food-add-banana").click();
  await expect(app.id("toast-message")).toContainText("Dinner");
  await expect.poll(async () => (await app.api("/dashboard")).body.meals.map((m: { meal_type: string }) => m.meal_type).sort()).toEqual(["breakfast", "dinner", "lunch", "snack"]);
});

test("food: the photo path is still there from the same screen", async ({ app }) => {
  await app.newUserOnToday("foodphoto");
  await openLogFood(app);
  // "Snap your meal" opens the picker at once; leave it empty and the choices stay on screen.
  app.page.once("filechooser", (chooser) => chooser.setFiles([]));
  await app.id("photo-mode-button").click();
  await expect(app.id("photo-logger")).toBeVisible();
  await expect(app.id("choose-photo-button")).toBeVisible();
  await app.id("photo-back-button").click();
  await expect(app.id("food-search-input")).toBeVisible();
  // The Coach camera button opens straight to the photo path.
  await app.id("log-food-close").click();
  await app.tab("Coach");
  await app.id("coach-photo-button").click();
  await expect(app.id("photo-logger")).toBeVisible();
});

test("food: Telugu strings on the log food screen", async ({ app }) => {
  await app.newUserOnToday("foodte");
  await app.id("open-settings-button").click();
  await app.page.getByText("తెలుగు", { exact: true }).click();
  await app.id("settings-close").click();
  await openLogFood(app);
  await expect(app.id("log-food-screen")).toContainText("ఆహారం లాగ్ చేయండి");
  await expect(app.id("food-search-input")).toHaveAttribute("placeholder", "ఆహారం వెతకండి, ఉదా. గుడ్డు, దోశ, పప్పు");
  await expect(app.id("chip-dosa")).toContainText("దోశ");
  await app.id("food-search-input").fill("దోశ");
  await expect(app.id("food-row-plain-dosa")).toBeVisible();
  await expect(app.id("food-row-plain-dosa")).toContainText("సాదా దోశ");
  await app.shot("telugu");
  const text = await app.text();
  expect(text.match(/\b[a-z]+[A-Z][A-Za-z]+\b/g) || [], "no raw keys").toEqual([]);
});
