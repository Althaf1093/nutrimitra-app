import { expect, test, uniqueEmail, type App } from "../fixtures";

// Feature 1, item 3: swap a meal, "I ate something else", and the evening check-in.

const KITCHEN = ["rice", "wheat-flour", "toor-dal", "moong-dal", "tomato", "onion", "potato", "brinjal", "okra", "spinach", "curd", "milk", "paneer", "banana", "apple", "peanuts", "idli-batter", "oats", "bread", "besan", "sprouts"];

async function kitchenUser(app: App, prefix: string) {
  await app.open();
  await app.signUp(uniqueEmail(prefix));
  await app.onboardWithKitchen(KITCHEN);
}

const todayCard = (app: App, slot: string) => app.id("today-screen").getByTestId(`meal-card-${slot}`);

test("daily: swap a meal for another from the same kitchen", async ({ app }) => {
  await kitchenUser(app, "kswap");
  const before = await todayCard(app, "lunch").innerText();
  await app.id("today-screen").getByTestId("swap-meal-lunch").click();
  await expect(app.id("swap-sheet")).toBeVisible();
  for (const index of [0, 1, 2]) await expect(app.id(`swap-option-${index}`)).toBeVisible();
  await expect(app.id("swap-option-3")).toHaveCount(0);
  await app.shot("swap-sheet");
  const chosen = (await app.id("swap-option-1").locator("text=/kcal/").first().innerText()).length > 0 ? await app.id("swap-option-1").innerText() : "";
  const chosenName = chosen.split("\n")[0];
  await app.id("swap-use-1").click();
  await expect(app.id("swap-sheet")).toHaveCount(0);
  await expect(app.id("toast-message")).toHaveText("Meal swapped");
  await expect(todayCard(app, "lunch")).toContainText(chosenName);
  expect(await todayCard(app, "lunch").innerText()).not.toBe(before);
  const plan = (await app.api("/plan")).body;
  expect(plan.days[plan.today_index].meals.find((m: { type: string }) => m.type === "lunch").name).toBe(chosenName);
  expect(plan.also_buy.length).toBeLessThanOrEqual(4);
  await app.shot("swapped");
});

test("daily: I ate something else logs for that slot and marks the planned meal", async ({ app }) => {
  await kitchenUser(app, "kelse");
  await app.id("today-screen").getByTestId("ate-else-breakfast").click();
  await expect(app.id("log-food-screen")).toBeVisible();
  await app.id("food-search-input").fill("banana");
  await app.id("food-add-banana").click();
  await expect(app.id("toast-message")).toContainText("Meal logged · Breakfast");
  await app.id("log-food-close").click();
  await expect(app.id("today-screen")).toBeVisible();
  await expect(app.id("today-screen").getByTestId("meal-ate-other-breakfast")).toHaveText("You logged something else for this meal");
  await expect(app.id("today-screen").getByTestId("swap-meal-lunch")).toBeVisible();
  await app.shot("ate-something-else");
});

test("daily: the evening check-in adapts tomorrow when protein was low", async ({ app }) => {
  await app.page.clock.setFixedTime(new Date("2026-10-20T10:00:00"));
  await kitchenUser(app, "kcheck");
  await expect(app.id("checkin-card")).toHaveCount(0); // only from the evening

  const calories = (await app.api("/dashboard")).body.target_calories as number;
  const logged = await app.api("/meals", { method: "POST", body: { meal_type: "lunch", name: "Plain rice and ghee", calories: Math.round(calories * 0.8), protein_g: 8, carbs_g: 120, fat_g: 20, source: "manual" } });
  expect(logged.status).toBe(200);
  await app.page.clock.setFixedTime(new Date("2026-10-20T19:00:00"));
  await app.page.reload();
  await expect(app.id("today-screen")).toBeVisible();
  await expect(app.id("checkin-card")).toBeVisible();
  await app.shot("checkin");
  await app.id("checkin-button").click();
  await expect(app.id("checkin-message")).toContainText("Protein was a little low today");
  await expect(app.id("toast-message")).toHaveText("Tomorrow's plan was adjusted.");
  await expect(app.id("checkin-button")).toHaveCount(0);
  await expect(app.id("checkin-numbers")).toContainText("g protein");
  await app.shot("checkin-done");

  const plan = (await app.api("/plan")).body;
  expect(plan.days[(plan.today_index + 1) % 7].focus).toBe("Protein-forward day");
  expect(plan.days[plan.today_index].focus).not.toBe("Protein-forward day");
  expect(plan.also_buy.length).toBeLessThanOrEqual(4);
  // Tomorrow, in the Plan tab.
  await app.tab("Plan");
  await app.id("plan-screen").getByTestId(`chip-day-${((plan.today_index + 1) % 7) + 1}`).click();
  await expect(app.id("plan-screen")).toContainText("Protein-forward day");
});

test("daily: a balanced day says so and changes nothing", async ({ app }) => {
  await app.page.clock.setFixedTime(new Date("2026-10-20T20:00:00"));
  await kitchenUser(app, "kbalance");
  const calories = (await app.api("/dashboard")).body.target_calories as number;
  const protein = Math.round((calories * 0.2) / 4) + 5;
  expect((await app.api("/meals", { method: "POST", body: { meal_type: "lunch", name: "A good lunch", calories, protein_g: protein, carbs_g: 200, fat_g: 60, source: "manual" } })).status).toBe(200);
  const before = (await app.api("/plan")).body;
  await app.page.reload();
  await app.id("checkin-button").click();
  await expect(app.id("checkin-message")).toContainText("A good balance today");
  const after = (await app.api("/plan")).body;
  expect(after.days.map((d: { focus: string }) => d.focus)).toEqual(before.days.map((d: { focus: string }) => d.focus));
});

test("daily: Telugu strings for swap, check-in and the replaced meal", async ({ app }) => {
  await app.page.clock.setFixedTime(new Date("2026-10-20T19:00:00"));
  await kitchenUser(app, "kdte");
  await app.page.evaluate(() => window.localStorage.setItem("nutrimitra.lang", JSON.stringify("te")));
  await app.page.reload();
  await expect(app.id("today-screen")).toBeVisible();
  await expect(app.id("checkin-card")).toContainText("సాయంత్రం చెక్-ఇన్");
  await expect(app.id("checkin-button")).toContainText("చెక్-ఇన్");
  await expect(app.id("today-screen").getByTestId("swap-meal-lunch")).toHaveText("మార్చు");
  await expect(app.id("today-screen").getByTestId("ate-else-lunch")).toHaveText("నేను వేరేది తిన్నాను");
  await app.id("today-screen").getByTestId("swap-meal-lunch").click();
  await expect(app.id("swap-sheet")).toContainText("ఈ భోజనాన్ని మార్చండి");
  await app.shot("telugu-swap");
  expect((await app.text()).match(/\b[a-z]+[A-Z][A-Za-z]+\b/g) || []).toEqual([]);
});
