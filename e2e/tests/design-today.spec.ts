import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test } from "../fixtures";

// Design run, item 3: Today with the calorie ring and macro bars, the coloured meal tiles, water, movement and the Coach card.
const SIZES = { phone: { width: 390, height: 844 }, tablet: { width: 820, height: 1180 }, desktop: { width: 1440, height: 900 } } as const;
const TALL = { phone: { width: 390, height: 1900 }, tablet: { width: 820, height: 1900 }, desktop: { width: 1440, height: 1100 } } as const;
const DIR = path.join(__dirname, "..", "screenshots", "design");

test("design: Today shows the ring, three macro bars, the Coach note and a water card that adds and takes back", async ({ app }) => {
  await app.newUserOnToday("todaycards");
  await expect(app.id("today-ring")).toBeVisible();
  for (const id of ["macro-protein", "macro-carbs", "macro-fat", "macro-fibre"]) await expect(app.id(id)).toBeVisible();
  await expect(app.id("coach-card-text")).toContainText("Add your first meal");
  await expect(app.id("macro-fibre")).toContainText("—"); // no meal has a fibre figure, so no made-up number
  // "What should I eat now?" lives in the Coach card, with three suggestion chips.
  await expect(app.id("coach-card").getByTestId("eat-now-button")).toBeVisible();
  await expect(app.id("coach-card").getByRole("button")).toHaveCount(4);
  // Water: each tap adds a glass and the card follows; minus appears once there is something to take back.
  await expect(app.id("water-minus")).toHaveCount(0);
  await app.id("water-plus").click();
  await app.id("water-plus").click();
  await expect(app.id("water-value")).toContainText("0.5");
  await app.id("water-minus").click();
  await expect(app.id("water-value")).toContainText("0.3");
  // It is saved: after a reload the same number is there.
  await app.page.reload();
  await expect(app.id("water-value")).toContainText("0.3");
});

test("design: on a wide screen Today has two columns and the header buttons", async ({ app }) => {
  await app.newUserOnToday("todaywide");
  await app.page.setViewportSize(SIZES.desktop);
  await expect(app.id("header-add-food")).toBeVisible();
  await expect(app.id("header-snap-meal")).toBeVisible();
  await expect(app.id("week-strip")).toHaveCount(0);
  const meals = await app.id("slot-breakfast").boundingBox();
  const lunch = await app.id("slot-lunch").boundingBox();
  expect(Math.abs(meals!.y - lunch!.y)).toBeLessThan(4); // two slot cards sit side by side
  const water = await app.id("water-card").boundingBox();
  expect(water!.x).toBeGreaterThan(meals!.x + meals!.width); // water is in the right-hand column
  await app.id("header-add-food").click();
  await expect(app.id("log-food-screen")).toBeVisible();
});

test("design: Today screenshots at three sizes, light and dark, English and Telugu", async ({ app }) => {
  mkdirSync(DIR, { recursive: true });
  await app.newUserOnToday("todayshots");
  await app.id("water-plus").click();
  for (const lang of ["en", "te"] as const) {
    await app.page.evaluate((value) => window.localStorage.setItem("nutrimitra.lang", JSON.stringify(value)), lang);
    await app.page.reload();
    await expect(app.id("today-screen")).toBeVisible();
    for (const scheme of ["light", "dark"] as const) {
      await app.page.emulateMedia({ colorScheme: scheme });
      for (const [size, viewport] of Object.entries(TALL)) {
        await app.page.setViewportSize(viewport);
        await expect(app.id("today-ring")).toBeVisible();
        await app.page.screenshot({ path: path.join(DIR, `today-full-${size}-${scheme}-${lang}.png`) });
      }
    }
  }
});

test("design: the verify-email prompt is a small banner that can be dismissed", async ({ app }) => {
  await app.newUserOnToday("verifybanner");
  const banner = app.id("verify-banner");
  await expect(banner).toBeVisible();
  expect((await banner.boundingBox())!.height).toBeLessThan(64);
  await app.id("verify-banner-dismiss").click();
  await expect(banner).toHaveCount(0);
});

for (const [name, viewport] of Object.entries({ phone: SIZES.phone, desktop: SIZES.desktop })) {
  test(`design: Today slot cards have no nested buttons and no console errors (${name})`, async ({ app }) => {
    await app.newUserOnToday(`nested${name}`);
    await app.page.setViewportSize(viewport);
    const meal = { meal_type: "lunch", name: "Dal rice", portion: "1 plate", calories: 450, protein_g: 15, carbs_g: 70, fat_g: 10 };
    const saved = await app.api("/meals", { method: "POST", body: meal });
    await app.page.reload();
    await expect(app.id("slot-lunch")).toBeVisible();
    // No <button> sits inside another <button> (or link) anywhere on the page.
    const nested = await app.page.evaluate(() => document.querySelectorAll("button button, a button, button a, [role=button] [role=button], button [role=button], [role=button] button").length);
    expect(nested).toBe(0);
    const id = saved.body.id;
    await app.id(`edit-meal-${id}`).click();
    await expect(app.id(`logged-meal-${id}`)).toHaveCount(0);
    expect(await app.page.evaluate(() => document.querySelectorAll("button button, [role=button] [role=button]").length)).toBe(0);
    await app.page.getByRole("button", { name: /cancel|రద్దు/i }).first().click();
    await expect(app.id(`logged-meal-${id}`)).toBeVisible();
    for (const testId of ["add-food-lunch", "snap-meal-lunch"]) {
      await expect(app.id(testId)).toBeEnabled();
    }
    await app.id(`remove-meal-${id}`).click();
    await expect(app.id(`logged-meal-${id}`)).toHaveCount(0);
    // The Undo toast has a button inside it; that must not be a button inside a button.
    await expect(app.id("toast-action")).toBeVisible();
    expect(await app.page.evaluate(() => document.querySelectorAll("button button, [role=button] [role=button]").length)).toBe(0);
    await app.id("toast-action").click();
    await expect(app.id(`logged-meal-${id}`).or(app.id("slot-lunch").getByText("Dal rice"))).toBeVisible();
    await app.id("add-food-dinner").click();
    await expect(app.id("log-food-screen")).toBeVisible();
  });
}
