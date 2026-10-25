import { expect, MEAL_IMAGE, test, type App } from "../fixtures";

// Logging run item 4: the kitchen from a big list with group tabs, and "Snap your kitchen".

async function toKitchenStep(app: App, diet?: string) {
  await app.open();
  await app.signUp(`kbig.${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}@example.com`);
  await expect(app.id("onboarding-screen")).toBeVisible();
  await app.id("field-age").fill("30");
  await app.id("onboarding-next-button").click();
  if (diet) {
    await app.id("chip-vegetarian").click();
    await app.id(`chip-${diet}`).click();
  }
  await app.id("onboarding-next-button").click();
  await app.id("onboarding-next-button").click();
  await expect(app.id("kitchen-editor")).toBeVisible();
}

test("kitchen: group tabs show one group at a time, and the big list is searchable", async ({ app }) => {
  await toKitchenStep(app);
  await expect(app.id("kitchen-tabs")).toBeVisible();
  for (const id of ["all", "vegetables", "staples", "spices", "condiments"]) await expect(app.id(`chip-tab-${id}`)).toBeVisible();
  await app.id("chip-tab-spices").click();
  await expect(app.id("kitchen-group-spices")).toBeVisible();
  await expect(app.id("kitchen-group-vegetables")).toHaveCount(0);
  await app.shot("kitchen-tab-spices");
  await app.id("chip-tab-all").click();
  await expect(app.id("kitchen-group-vegetables")).toBeVisible();

  await app.id("kitchen-search").fill("basmati");
  await expect(app.id("kitchen-results")).toContainText("Basmati rice");
  await app.id("kitchen-search").fill("ajwain");
  await expect(app.id("kitchen-results")).toContainText("Carom seeds");
  await app.id("kitchen-search").fill("");
});

test("kitchen: snap your kitchen lists what the photo shows, you untick, and only then it is added", async ({ app }) => {
  await toKitchenStep(app, "eggetarian");
  await app.id("chip-brinjal").click();
  const chooser = app.page.waitForEvent("filechooser");
  await app.id("kitchen-snap").click();
  await (await chooser).setFiles(MEAL_IMAGE);

  await expect(app.id("kitchen-snap-review")).toBeVisible();
  await app.shot("kitchen-snap-review");
  // The fake vision model lists tomato, onion, toor dal, curd, chicken and a sauce that is not in the catalogue.
  // The chosen diet is eggetarian, so chicken is dropped quietly.
  for (const id of ["tomato", "onion", "toor-dal", "curd"]) await expect(app.id(`chip-snap-${id}`)).toBeVisible();
  await expect(app.id("chip-snap-chicken")).toHaveCount(0);
  await expect(app.id("kitchen-snap-unmatched")).toContainText("mystery sauce");
  // Nothing is added yet.
  await expect(app.id("kitchen-count")).toHaveText("1 selected");

  await app.id("chip-snap-onion").click(); // untick
  await app.id("kitchen-snap-add").click();
  await expect(app.id("kitchen-snap-panel")).toHaveCount(0);
  await expect(app.id("kitchen-count")).toHaveText("4 selected"); // brinjal, tomato, toor dal, curd
  await app.id("onboarding-next-button").click();
  await expect(app.id("today-screen")).toBeVisible();
  const saved = (await app.api("/kitchen")).body;
  expect([...saved.kitchen.items].sort()).toEqual(["brinjal", "curd", "tomato", "toor-dal"]);
});

test("kitchen: cancelling a snap adds nothing", async ({ app }) => {
  await toKitchenStep(app);
  const chooser = app.page.waitForEvent("filechooser");
  await app.id("kitchen-snap").click();
  await (await chooser).setFiles(MEAL_IMAGE);
  await expect(app.id("kitchen-snap-review")).toBeVisible();
  await app.id("kitchen-snap-cancel").click();
  await expect(app.id("kitchen-snap-panel")).toHaveCount(0);
  await expect(app.id("kitchen-count")).toHaveText("0 selected");
});
