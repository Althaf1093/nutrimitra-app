import { expect, test } from "../fixtures";
import path from "node:path";

// Only runs with the real providers: set E2E_REAL_VISION=1 (needs GEMINI_API_KEY and/or GROQ_API_KEY in backend/.env).
// The default stack replaces every AI provider with a fake, so this is kept out of the normal run.
test.skip(!process.env.E2E_REAL_VISION, "set E2E_REAL_VISION=1 to run against the real vision providers");

test("photo logging against the real vision provider", async ({ app }) => {
  test.setTimeout(240_000);
  await app.newUserOnToday("realphoto");
  await app.id("log-food-button").click();
  const chooser = app.page.waitForEvent("filechooser");
  await app.id("photo-mode-button").click();
  await (await chooser).setFiles(path.join(__dirname, "..", "fixtures", "meal.jpg"));

  await expect(app.id("vision-confirm")).toBeVisible({ timeout: 120_000 });
  expect((await app.id("vision-field-name").inputValue()).length).toBeGreaterThan(2);
  await app.shot("real-confirm");
  await app.id("vision-confirm-button").click();
  await expect(app.id("today-screen")).toBeVisible();
  const meal = (await app.api("/dashboard")).body.meals[0];
  expect(meal.calories).toBeGreaterThan(0);
  expect(meal.source).toBe("photo estimate");
});
