import { expect, test } from "../fixtures";

// The feedback toast: a small light pill above the tab bar that goes away by itself, never a full-width black bar.

test("toast: small light pill, optimistic log, auto-dismiss, Undo for log and remove @desktop", async ({ app }) => {
  await app.newUserOnToday("toast");
  const toast = app.id("toast");
  const viewport = app.page.viewportSize()!;

  const started = Date.now();
  await app.id("suggestion-toggle-breakfast").click();
  await app.id("log-suggestion-breakfast").click();
  // Optimistic: the suggestion is already gone, without waiting for the reload.
  await expect(app.id("suggestion-toggle-breakfast")).toHaveCount(0);
  await expect(app.id("toast-message")).toHaveText("Meal logged");
  await expect(toast).toHaveAttribute("role", "status");
  await app.shot("toast-logged");

  // Small and centred, not a full-width slab; sitting above the tab bar, not over the meals list's end.
  const box = (await toast.boundingBox())!;
  expect(box.width).toBeLessThanOrEqual(420);
  expect(box.width).toBeLessThan(viewport.width - 24);
  expect(Math.abs(box.x + box.width / 2 - viewport.width / 2)).toBeLessThan(8);
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height - 64);
  const pill = toast.getByRole("button").first();
  const [red, green, blue] = (await pill.evaluate((el) => getComputedStyle(el).backgroundColor)).match(/\d+/g)!.map(Number);
  expect((red + green + blue) / 3, "a light card, not a black bar").toBeGreaterThan(200);

  // It leaves on its own: gone within a few seconds, with nobody tapping it.
  await expect(toast).toHaveCount(0, { timeout: 8_000 });
  const shown = Date.now() - started;
  expect(shown).toBeGreaterThan(1_500);
  expect(shown).toBeLessThan(8_000);
  await app.shot("toast-gone");

  // Remove, then Undo brings the meal back.
  await app.idStarting("remove-meal-").click();
  await expect(app.id("toast-message")).toHaveText("Removed");
  await expect(app.id("today-empty")).toBeVisible();
  await app.id("toast-action").click();
  await expect(app.id("today-empty")).toHaveCount(0);
  await expect(toast).toHaveCount(0);
  await expect.poll(async () => (await app.api("/dashboard")).body.meals.length).toBe(1);

  // Logging another activity shows one toast at a time: a new toast replaces the old one.
  await app.id("log-walk-button").click();
  await expect(app.id("toast-message")).toHaveText("Activity logged");
  await app.id("log-strength-button").click();
  await expect(toast).toHaveCount(1);

  // Tapping dismisses.
  await toast.getByRole("button").first().click();
  await expect(toast).toHaveCount(0);

  // Undo of a log removes the entry again.
  await app.id("log-walk-button").click();
  await app.id("toast-action").click();
  await expect(app.id("toast-message")).toHaveText("Undone");
  await expect.poll(async () => (await app.api("/dashboard")).body.activities.length).toBe(2);
});

test("toast: an error is announced as an alert and the log rolls back", async ({ app }) => {
  app.allow(/http 5\d\d POST .*\/meals/, /console\.error Failed to load resource.*50\d/);
  await app.newUserOnToday("toasterr");
  await app.page.route("**/api/meals", (route) => (route.request().method() === "POST" ? route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Something went wrong. Please try again." }) }) : route.continue()));
  await app.id("suggestion-toggle-breakfast").click();
  await app.id("log-suggestion-breakfast").click();
  await expect(app.id("toast")).toHaveAttribute("role", "alert");
  await expect(app.id("toast-icon-error")).toBeVisible();
  // Rolled back: the suggestion is back, nothing was logged.
  await expect(app.id("log-suggestion-breakfast")).toBeVisible();
  await expect(app.id("today-empty")).toBeVisible();
  await app.shot("toast-error");
});
