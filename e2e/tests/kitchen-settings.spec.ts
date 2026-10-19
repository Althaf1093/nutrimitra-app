import { expect, test, uniqueEmail, type App } from "../fixtures";

// Feature 1, item 4: Settings > My Kitchen, and the prompt to update the plan.

async function openKitchen(app: App) {
  await app.id("open-settings-button").click();
  await expect(app.id("settings-screen")).toBeVisible();
  await app.id("open-kitchen").click();
  await expect(app.id("kitchen-screen")).toBeVisible();
}

test("settings kitchen: set it up later, then update the plan", async ({ app }) => {
  await app.newUserOnToday("kset");
  await app.id("open-settings-button").click();
  await expect(app.id("kitchen-summary")).toHaveText("Not set up yet");
  await app.shot("settings-row");
  await app.id("open-kitchen").click();
  await expect(app.id("kitchen-editor")).toBeVisible();
  await expect(app.id("chip-chicken")).toHaveCount(0); // the saved profile is vegetarian: the server hides it
  for (const id of ["brinjal", "tomato", "onion", "rice", "toor-dal", "curd"]) await app.id(`chip-${id}`).click();
  await app.id("chip-meals-2").click();
  await app.id("kitchen-save").click();
  await expect(app.id("toast-message")).toHaveText("Kitchen saved");
  await expect(app.id("kitchen-saved-card")).toContainText("Update your plan so it uses these ingredients?");
  await app.shot("saved-prompt");
  expect((await app.api("/kitchen")).body.kitchen).toMatchObject({ meals_per_day: 2 });
  // The plan made before the kitchen existed is now out of date.
  expect((await app.api("/plan")).body.kitchen_changed).toBe(true);

  await app.id("kitchen-update-plan").click();
  await expect(app.id("toast-message")).toHaveText("Plan refreshed");
  await expect(app.id("kitchen-saved-card")).toContainText("Plan refreshed");
  const plan = (await app.api("/plan")).body;
  expect(plan.kitchen_based).toBe(true);
  expect(plan.kitchen_changed).toBe(false);
  expect(plan.generated_by).toBe("groq kitchen engine");
  await app.id("kitchen-done").click();
  await expect(app.id("settings-screen")).toBeVisible();
  await expect(app.id("kitchen-summary")).toContainText("6 ingredients");
  await app.id("settings-close").click();
  await app.tab("Plan");
  await expect(app.id("plan-from-kitchen")).toBeVisible();
});

test("settings kitchen: change an existing kitchen and say not now", async ({ app }) => {
  await app.open();
  await app.signUp(uniqueEmail("kedit"));
  await app.onboardWithKitchen(["rice", "toor-dal", "tomato"]);
  await app.tab("Plan");
  await expect(app.id("plan-from-kitchen")).toBeVisible();
  await app.tab("Today");
  await openKitchen(app);
  await expect(app.id("kitchen-count")).toHaveText("3 selected");
  await app.id("chip-rice").click();
  await app.id("chip-potato").click();
  await app.id("chip-okra").click();
  await expect(app.id("kitchen-count")).toHaveText("4 selected");
  await app.id("kitchen-save").click();
  await app.id("kitchen-not-now").click();
  await expect(app.id("settings-screen")).toBeVisible();
  expect([...(await app.api("/kitchen")).body.kitchen.items].sort()).toEqual(["okra", "potato", "tomato", "toor-dal"]);
  // Not now: the plan keeps asking, in the Plan tab.
  await app.id("settings-close").click();
  await app.tab("Plan");
  await app.page.reload();
  await app.tab("Plan");
  await expect(app.id("plan-kitchen-changed")).toBeVisible();
});

test("settings kitchen: a non-vegetarian can pick chicken, a saved kitchen is refused chicken after a diet change", async ({ app }) => {
  await app.open();
  await app.signUp(uniqueEmail("kdiet"));
  await app.onboardWithKitchen(["chicken", "rice"], { diet: "non-vegetarian" });
  await openKitchen(app);
  await expect(app.id("chip-chicken")).toBeVisible();
  await expect(app.id("kitchen-count")).toHaveText("2 selected");
  const refused = await app.api("/profile", { method: "PUT", body: { age: 30, sex: "Prefer not to say", height_cm: 165, weight_kg: 70, target_weight_kg: 65, conditions: [], dietary_preferences: ["Vegetarian"], allergies: [], disliked_foods: [], activity_level: "Moderately active", cooking_time: "20–30 min", food_budget: "Balanced", wellness_goal: "Healthier living", language: "en", timezone: "Asia/Kolkata" } });
  expect(refused.status).toBe(200);
  // The diet changed: chicken is gone from what the kitchen shows.
  expect((await app.api("/kitchen")).body.kitchen.items).toEqual(["rice"]);
  const again = await app.api("/kitchen", { method: "PUT", body: { items: ["rice", "chicken"], meals_per_day: 3, household_size: 2 } });
  expect(again.status).toBe(422);
});

test("settings kitchen: Telugu", async ({ app }) => {
  await app.newUserOnToday("kstel");
  await app.page.evaluate(() => window.localStorage.setItem("nutrimitra.lang", JSON.stringify("te")));
  await app.page.reload();
  await app.id("open-settings-button").click();
  await expect(app.id("open-kitchen")).toContainText("నా వంటగది");
  await expect(app.id("kitchen-summary")).toHaveText("ఇంకా సెట్ చేయలేదు");
  await app.id("open-kitchen").click();
  await expect(app.id("kitchen-screen")).toContainText("నా వంటగది");
  await app.id("chip-brinjal").click();
  await app.id("kitchen-save").click();
  await expect(app.id("kitchen-saved-card")).toContainText("వంటగది సేవ్ అయింది");
  await expect(app.id("kitchen-update-plan")).toContainText("ప్లాన్ నవీకరించు");
  await app.shot("telugu");
  expect((await app.text()).match(/\b[a-z]+[A-Z][A-Za-z]+\b/g) || []).toEqual([]);
});
