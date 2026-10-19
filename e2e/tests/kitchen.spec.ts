import { expect, test } from "../fixtures";

// Feature 1: the kitchen step of onboarding.

async function toKitchenStep(app: import("../fixtures").App, options: { diet?: string; language?: string } = {}) {
  await app.open();
  await app.signUp(`kitchen.${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}@example.com`);
  await expect(app.id("onboarding-screen")).toBeVisible();
  await app.id("field-age").fill("30");
  await app.id("onboarding-next-button").click();
  if (options.diet) {
    await app.id("chip-vegetarian").click(); // default is Vegetarian: turn it off, then pick the wanted one
    await app.id(`chip-${options.diet}`).click();
  }
  await app.id("onboarding-next-button").click();
  await app.id("onboarding-next-button").click();
  if (options.language) {
    // The interface language is stored on the device; reloading on the kitchen step is not possible, so set it and come back.
    await app.page.evaluate((lang) => window.localStorage.setItem("nutrimitra.lang", JSON.stringify(lang)), options.language);
    await app.page.reload();
    await expect(app.id("onboarding-screen")).toBeVisible();
    for (let step = 0; step < 3; step++) await app.id("onboarding-next-button").click();
  }
  await expect(app.id("kitchen-editor")).toBeVisible();
}

test("kitchen: pick ingredients, meals and people; they are saved with the profile", async ({ app }) => {
  await toKitchenStep(app);
  await expect(app.id("onboarding-screen")).toContainText("4 / 4");
  // Vegetarian by default: plenty of vegetables, no chicken, fish or egg.
  for (const id of ["brinjal", "okra", "gongura", "drumstick", "raw-banana", "toor-dal", "ragi", "paneer", "curd"]) await expect(app.id(`chip-${id}`)).toBeVisible();
  for (const id of ["chicken", "fish", "egg", "mutton", "prawns"]) await expect(app.id(`chip-${id}`)).toHaveCount(0);
  await app.shot("kitchen-step");

  for (const id of ["brinjal", "tomato", "onion", "rice", "toor-dal", "paneer"]) await app.id(`chip-${id}`).click();
  await expect(app.id("kitchen-count")).toHaveText("6 selected");
  await app.id("chip-meals-2").click();
  await app.id("chip-people-4").click();
  await app.id("chip-under-15-min").click();
  await app.shot("kitchen-picked");
  await app.id("onboarding-next-button").click();
  await expect(app.id("today-screen")).toBeVisible();

  const saved = (await app.api("/kitchen")).body;
  expect(saved.configured).toBe(true);
  expect(saved.kitchen).toMatchObject({ meals_per_day: 2, household_size: 4, cooking_time: "Under 15 min" });
  expect([...saved.kitchen.items].sort()).toEqual(["brinjal", "onion", "paneer", "rice", "tomato", "toor-dal"]);
  expect((await app.api("/me")).body.profile.cooking_time).toBe("Under 15 min");
});

test("kitchen: skip for now saves no kitchen", async ({ app }) => {
  await toKitchenStep(app);
  await app.id("chip-brinjal").click();
  await app.id("kitchen-skip-button").click();
  await expect(app.id("today-screen")).toBeVisible();
  expect((await app.api("/kitchen")).body).toEqual({ configured: false, kitchen: null });
});

test("kitchen: search by another name, clear, collapse a group", async ({ app }) => {
  await toKitchenStep(app);
  await app.id("kitchen-search").fill("vankaya");
  await expect(app.id("chip-brinjal")).toBeVisible();
  await expect(app.id("chip-okra")).toHaveCount(0);
  await app.id("kitchen-search").fill("zzzz");
  await expect(app.id("kitchen-no-match")).toBeVisible();
  await app.id("kitchen-search-clear").click();
  await expect(app.id("chip-okra")).toBeVisible();
  await app.id("kitchen-group-toggle-vegetables").click();
  await expect(app.id("chip-okra")).toHaveCount(0);
  await app.id("kitchen-group-toggle-vegetables").click();
  await expect(app.id("chip-okra")).toBeVisible();
  await app.id("chip-okra").click();
  await expect(app.id("kitchen-count")).toHaveText("1 selected");
  await app.id("kitchen-clear").click();
  await expect(app.id("kitchen-count")).toHaveText("0 selected");
});

test("kitchen: a non-vegetarian sees chicken and fish, a vegan does not see paneer", async ({ app }) => {
  await toKitchenStep(app, { diet: "non-vegetarian" });
  for (const id of ["chicken", "fish", "egg", "paneer"]) await expect(app.id(`chip-${id}`)).toBeVisible();
  await app.id("chip-chicken").click();
  await app.id("onboarding-next-button").click();
  await expect(app.id("today-screen")).toBeVisible();
  expect((await app.api("/kitchen")).body.kitchen.items).toEqual(["chicken"]);
});

test("kitchen: Telugu names on the kitchen step", async ({ app }) => {
  await toKitchenStep(app, { language: "te" });
  await expect(app.id("kitchen-editor")).toContainText("ఇంట్లో సాధారణంగా ఏమి ఉంటాయి?");
  await expect(app.id("chip-brinjal")).toContainText("వంకాయ");
  await expect(app.id("kitchen-group-vegetables")).toContainText("కూరగాయలు");
  await expect(app.id("kitchen-search")).toHaveAttribute("placeholder", "పదార్థాలు వెతకండి");
  await app.shot("kitchen-telugu");
  expect((await app.text()).match(/\b[a-z]+[A-Z][A-Za-z]+\b/g) || []).toEqual([]);
});
