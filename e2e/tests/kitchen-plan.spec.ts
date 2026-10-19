import { expect, setAi, test, uniqueEmail } from "../fixtures";

// Feature 1, item 2: a plan built from the kitchen, the shopping list, and the "kitchen changed" prompt.

const KITCHEN = ["rice", "toor-dal", "tomato", "onion", "potato", "curd", "banana", "wheat-flour"];
const MEAT = /chicken|mutton|fish|prawn|egg /i;

test("kitchen plan: meals use the kitchen, the shopping list says nothing is needed", async ({ app }) => {
  await app.open();
  await app.signUp(uniqueEmail("kplan"));
  await app.onboardWithKitchen(KITCHEN);

  await app.tab("Plan");
  await expect(app.id("plan-screen")).toBeVisible();
  await expect(app.id("plan-from-kitchen")).toHaveText("Built from your kitchen");
  const planScreen = app.id("plan-screen");
  await expect(planScreen.getByTestId("meal-uses-breakfast")).toBeVisible();
  const uses = (await planScreen.getByTestId("meal-uses-breakfast").innerText()).toLowerCase();
  expect(uses.startsWith("uses:")).toBe(true);
  expect(uses).toMatch(/rice|dal|tomato|onion|potato|curd|banana|wheat/);
  await expect(app.id("plan-also-buy")).toHaveCount(0);
  await expect(app.id("plan-kitchen-changed")).toHaveCount(0);
  const plan = (await app.api("/plan")).body;
  expect(plan.kitchen_based).toBe(true);
  expect(plan.generated_by).toBe("groq kitchen engine");
  expect(JSON.stringify(plan.days)).not.toMatch(MEAT);
  await app.shot("kitchen-plan");

  await app.id("open-shopping-list").click();
  await expect(app.id("shopping-list-screen")).toBeVisible();
  await expect(app.id("shopping-for")).toHaveText("Cooking for 2");
  await expect(app.id("shopping-empty")).toBeVisible();
  await expect(app.id("shopping-have")).toContainText("Rice");
  await app.shot("shopping-list");
  await app.id("shopping-list-close").click();
  await expect(app.id("plan-screen")).toBeVisible();
});

test("kitchen plan: when the AI is busy the kitchen engine still makes the plan", async ({ app }) => {
  await app.open();
  await app.signUp(uniqueEmail("kbusy"));
  await app.onboardWithKitchen(KITCHEN);
  await app.tab("Plan");
  await expect(app.id("plan-from-kitchen")).toBeVisible();
  await setAi("busy");
  try {
    await app.id("refresh-plan-button").click();
    await expect(app.id("toast-message")).toHaveText("Plan refreshed");
    await expect(app.id("toast-icon-error")).toHaveCount(0);
    expect((await app.api("/plan")).body.generated_by).toBe("Wellstride kitchen engine");
    await expect(app.id("plan-from-kitchen")).toBeVisible();
    await expect(app.id("plan-screen").getByTestId("meal-uses-lunch")).toBeVisible();
  } finally {
    await setAi("ok");
  }
});

test("kitchen plan: changing the kitchen prompts to update the plan", async ({ app }) => {
  await app.open();
  await app.signUp(uniqueEmail("kchange"));
  await app.onboardWithKitchen(KITCHEN);
  await app.tab("Plan");
  await expect(app.id("plan-from-kitchen")).toBeVisible();
  await expect(app.id("plan-kitchen-changed")).toHaveCount(0);

  const saved = await app.api("/kitchen", { method: "PUT", body: { items: [...KITCHEN, "ragi", "okra"], meals_per_day: 3, household_size: 2, cooking_time: "20–30 min" } });
  expect(saved.status).toBe(200);
  await app.page.reload();
  await app.tab("Plan");
  await expect(app.id("plan-kitchen-changed")).toBeVisible();
  await app.shot("kitchen-changed");
  await app.id("plan-update-button").click();
  await expect(app.id("toast-message")).toHaveText("Plan refreshed");
  await expect(app.id("plan-kitchen-changed")).toHaveCount(0);
});

test("kitchen plan: no kitchen means the shopping list asks to set one up", async ({ app }) => {
  await app.newUserOnToday("kplain");
  await app.tab("Plan");
  await expect(app.id("plan-screen")).toBeVisible();
  await expect(app.id("plan-from-kitchen")).toHaveText("");
  await app.id("open-shopping-list").click();
  await expect(app.id("shopping-no-kitchen")).toBeVisible();
});

test("kitchen plan: shopping list in Telugu", async ({ app }) => {
  await app.open();
  await app.signUp(uniqueEmail("kte"));
  await app.onboardWithKitchen(KITCHEN);
  await app.page.evaluate(() => window.localStorage.setItem("nutrimitra.lang", JSON.stringify("te")));
  await app.page.reload();
  await expect(app.id("today-screen")).toBeVisible();
  await app.tab("ప్లాన్");
  await expect(app.id("plan-from-kitchen")).toHaveText("మీ వంటగది నుండి తయారైంది");
  await app.id("open-shopping-list").click();
  await expect(app.id("shopping-list-screen")).toContainText("కొనుగోలు జాబితా");
  await expect(app.id("shopping-have")).toContainText("బియ్యం");
  await app.shot("shopping-telugu");
});
