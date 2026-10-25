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
  for (const id of ["macro-protein", "macro-carbs", "macro-fat"]) await expect(app.id(id)).toBeVisible();
  await expect(app.id("coach-card-text")).toContainText("Add your first meal");
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
