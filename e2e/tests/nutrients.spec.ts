import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test } from "../fixtures";

// Nutrients PR 2: vitamins and minerals on Today and the weekly view.
const DIR = path.join(__dirname, "..", "screenshots", "design");
const RAJMA = { meal_type: "lunch", name: "Rajma masala", portion: "1 bowl", calories: 350, protein_g: 15, carbs_g: 50, fat_g: 10 };

test("nutrients: Today shows 'log a meal' first, then the three lowest, then all of them with sodium as a limit", async ({ app }) => {
  await app.newUserOnToday("nutrients");
  await expect(app.id("nutrients-none")).toBeVisible();
  await app.api("/meals", { method: "POST", body: { ...RAJMA, name: "Masala tea", meal_type: "snack", calories: 80 } });
  await app.page.reload();
  await expect(app.id("nutrients-none")).toBeVisible(); // tea is not tracked: nothing is shown as zero
  await app.api("/meals", { method: "POST", body: RAJMA });
  await app.page.reload();
  await expect(app.id("nutrients-list")).toBeVisible();
  await expect(app.id("nutrients-list").locator('[data-testid^="nutrient-"]')).toHaveCount(3);
  await expect(app.id("nutrients-card")).toContainText("not medical advice");
  await app.id("nutrients-toggle").click();
  await expect(app.id("nutrients-list").locator('[data-testid^="nutrient-"]')).toHaveCount(13);
  await expect(app.id("nutrient-sodium")).toContainText("keep under");
  await expect(app.id("nutrient-iron")).toContainText("mg");
});

test("nutrients: the weekly card on the Progress tab is empty at first and then averages the days with food", async ({ app }) => {
  await app.newUserOnToday("nutrientweek");
  await app.tab("Progress");
  await expect(app.id("nutrients-week-empty")).toBeVisible();
  await app.api("/meals", { method: "POST", body: RAJMA });
  await app.page.reload();
  await expect(app.id("nutrients-week-card")).toContainText("1 day");
  await expect(app.id("nutrients-week-card")).not.toContainText("not tracked");
});

test("nutrients: Telugu names and words, and screenshots", async ({ app }) => {
  mkdirSync(DIR, { recursive: true });
  await app.newUserOnToday("nutrientste");
  await app.api("/meals", { method: "POST", body: RAJMA });
  await app.page.evaluate(() => window.localStorage.setItem("nutrimitra.lang", JSON.stringify("te")));
  await app.page.reload();
  await expect(app.id("nutrients-card")).toContainText("విటమిన్లు మరియు ఖనిజాలు");
  await app.id("nutrients-toggle").click();
  await expect(app.id("nutrient-iron")).toContainText("ఇనుము");
  for (const [name, viewport] of [["phone", { width: 390, height: 1100 }], ["desktop", { width: 1440, height: 1100 }]] as const) {
    await app.page.setViewportSize(viewport);
    await expect(app.id("nutrients-card")).toBeVisible();
    await app.id("nutrients-card").screenshot({ path: path.join(DIR, `nutrients-today-${name}-te.png`) });
  }
});
