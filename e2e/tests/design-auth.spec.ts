import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test } from "../fixtures";

// Design run, item 2: the welcome and sign-in screen, in three sizes, light and dark, Telugu and English.
const SIZES = { phone: { width: 390, height: 844 }, tablet: { width: 820, height: 1180 }, desktop: { width: 1440, height: 900 } } as const;
const DIR = path.join(__dirname, "..", "screenshots", "design");

test("design: welcome has the language picker, the hero, the three features and the form", async ({ app }) => {
  await app.open();
  await expect(app.id("language-toggle")).toBeVisible();
  await expect(app.id("auth-submit-button")).toBeVisible();
  await expect(app.page.getByText("Your kitchen. Your goal.", { exact: true })).toBeVisible();
  await expect(app.page.getByText("Snap or speak your meal")).toBeVisible();
  // Switching to Telugu changes the headline; switching back restores it.
  await app.id("language-toggle-te").click();
  await expect(app.page.getByText("మీ వంటగది. మీ లక్ష్యం.", { exact: true })).toBeVisible();
  await app.id("language-toggle-en").click();
  await expect(app.page.getByText("Your kitchen. Your goal.", { exact: true })).toBeVisible();
});

test("design: welcome screenshots at three sizes, light and dark, English and Telugu", async ({ app }) => {
  mkdirSync(DIR, { recursive: true });
  await app.open();
  for (const lang of ["en", "te"] as const) {
    await app.id(`language-toggle-${lang}`).click();
    for (const scheme of ["light", "dark"] as const) {
      await app.page.emulateMedia({ colorScheme: scheme });
      for (const [size, viewport] of Object.entries(SIZES)) {
        await app.page.setViewportSize(viewport);
        await expect(app.id("welcome-screen")).toBeVisible();
        await app.page.screenshot({ path: path.join(DIR, `welcome-${size}-${scheme}-${lang}.png`) });
      }
    }
  }
});
