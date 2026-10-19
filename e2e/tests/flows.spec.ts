import { expect, MEAL_IMAGE, PASSWORD, API, setAi, test, uniqueEmail } from "../fixtures";

// One test per flow from docs/E2E_PROMPT.md. Each creates its own throwaway user through the real sign-up screen;
// the whole test database is deleted when the run ends.

test("1. sign up, sign out, sign in again, wrong password @desktop", async ({ app }) => {
  app.allow(/http 401 POST .*\/auth\/login/, /console\.error Failed to load resource.*401/);
  const email = uniqueEmail("flow1");
  await app.open();
  await app.shot("welcome");
  await app.signUp(email);
  await expect(app.id("onboarding-screen")).toBeVisible();
  await app.completeOnboarding();
  await app.shot("today");

  await app.id("open-settings-button").click();
  await expect(app.id("settings-screen")).toBeVisible();
  await app.id("sign-out-button").click();
  await expect(app.id("welcome-screen")).toBeVisible();

  await app.signIn(email, "WrongPass999");
  await expect(app.id("auth-error")).toHaveText("Email or password is incorrect");
  await app.shot("wrong-password");

  await app.signIn(email);
  await expect(app.id("today-screen")).toBeVisible();
  const me = await app.api("/me");
  expect(me.body.user.email).toBe(email);
});

test("1b. a backend that cannot be reached is explained, not a bare \"Failed to fetch\"", async ({ app }) => {
  app.allow(/requestfailed .*\/auth\/login/, /console\.error Failed to load resource/, /console\.error \[Wellstride\] Could not reach the backend/);
  await app.open();
  await app.page.route("**/api/auth/login", (route) => route.abort("failed"));
  await app.signIn(uniqueEmail("unreachable"));
  await expect(app.id("auth-error")).toHaveText("Can't reach the server. Check your connection and try again.");
  await app.shot("cannot-reach");
  // The browser console names what to check (backend address and the origin CORS must allow).
  const hint = app.issues.find((issue) => issue.text.includes("[Wellstride] Could not reach the backend"));
  expect(hint?.text).toContain("CORS_ORIGINS allows http://localhost:");
});

test("2. onboarding: three steps and the 18+ rule", async ({ app }) => {
  await app.open();
  await app.signUp(uniqueEmail("flow2"));
  await expect(app.id("onboarding-screen")).toBeVisible();
  await expect(app.id("age-note")).toContainText("18");

  // Under 18 is refused and the person stays on the first step.
  await app.id("field-age").fill("17");
  await app.id("onboarding-next-button").click();
  await expect(app.id("onboarding-error")).toContainText("18 or older");
  await expect(app.id("field-age")).toBeVisible();
  await app.shot("under-18");

  await app.id("field-age").fill("18");

  // Height can be typed in feet: 5.5 ft is about 168 cm, and the other unit is always echoed.
  await app.id("chip-ft").click();
  await app.id("field-height-(ft)").fill("5.5");
  await expect(app.id("height-echo")).toContainText("168 cm");
  await app.id("field-height-(ft)").fill("5'6");
  await expect(app.id("height-echo")).toContainText("168 cm");
  await app.id("field-height-(ft)").fill("1");
  await app.id("onboarding-next-button").click();
  await expect(app.id("onboarding-error")).toContainText("3 ft");
  await app.shot("height-feet");
  await app.id("chip-cm").click();
  await app.id("field-height-(cm)").fill("170");
  await expect(app.id("height-echo")).toContainText("5′7″");
  await app.id("field-current-weight-(kg)").fill("72");
  await app.id("field-target-weight-(kg)").fill("68");
  await app.id("onboarding-next-button").click();
  await expect(app.id("onboarding-error")).toHaveCount(0);

  await app.id("chip-weight-loss").click();
  await app.id("chip-vegan").click();
  await app.shot("step-2");
  await app.id("onboarding-next-button").click();

  await app.id("chip-very-active").click();
  await app.id("chip-under-15-min").click();
  await app.id("chip-budget-friendly").click();
  await app.shot("step-3");
  await app.id("onboarding-next-button").click();
  await expect(app.id("today-screen")).toBeVisible();

  const profile = (await app.api("/me")).body.profile;
  expect(profile).toMatchObject({ age: 18, height_cm: 170, weight_kg: 72, target_weight_kg: 68, wellness_goal: "Weight loss", activity_level: "Very active", cooking_time: "Under 15 min", food_budget: "Budget-friendly" });
  expect(profile.dietary_preferences).toContain("Vegan");
  expect(profile.timezone).toBeTruthy();
});

test("3. plan: today's day, refresh, and the AI-busy message", async ({ app }) => {
  app.allow(/http 503 POST .*\/plan\/regenerate/, /console\.error Failed to load resource.*503/);
  await app.newUserOnToday("flow3");
  await app.tab("Plan");
  await expect(app.id("plan-screen")).toBeVisible();
  await expect(app.page.getByText(/Day 1 · Today/)).toBeVisible();
  await expect(app.id("plan-screen").getByTestId("meal-card-breakfast")).toBeVisible();
  await expect(app.id("plan-wellness-notice")).toBeVisible();
  const first = (await app.api("/plan")).body;
  expect(first.today_index).toBe(0);
  await app.shot("plan");

  await app.id("refresh-plan-button").click();
  await expect(app.page.getByText("Plan refreshed")).toBeVisible();

  await setAi("busy");
  try {
    await app.id("refresh-plan-button").click();
    await expect(app.page.getByText("AI is busy, try again in a minute.")).toBeVisible({ timeout: 30_000 });
    await expect(app.id("plan-screen").getByTestId("meal-card-breakfast")).toBeVisible(); // the current plan is still shown
    await app.shot("ai-busy");
  } finally {
    await setAi("ok");
  }
});

test("4. today: log a plan meal, edit it, remove it @desktop", async ({ app }) => {
  await app.newUserOnToday("flow4");
  await expect(app.id("log-meal-breakfast")).toBeVisible();
  await expect(app.id("today-progress-calories")).toContainText("0");

  await app.id("log-meal-breakfast").click();
  await expect(app.id("meal-logged-breakfast")).toBeVisible();
  await expect(app.id("log-meal-breakfast")).toHaveCount(0); // no "+" left, so it cannot be logged twice
  await expect(app.id("logged-meals")).toBeVisible();
  await app.shot("logged");
  const double = await app.api("/meals", { method: "POST", body: { meal_type: "breakfast", name: (await app.api("/dashboard")).body.meals[0].name, calories: 400, protein_g: 10, carbs_g: 50, fat_g: 10, source: "plan" } });
  expect(double.status).toBe(409);

  await app.idStarting("edit-meal-").click();
  await app.id("field-calories-(kcal)").fill("300");
  await app.shot("editing");
  await app.idStarting("edit-meal-save-").click();
  await expect(app.id("logged-meals")).toContainText("300 kcal");
  await expect(app.id("today-progress-calories")).toContainText("300");
  expect((await app.api("/dashboard")).body.calories).toBe(300);

  await app.idStarting("remove-meal-").click();
  await expect(app.id("logged-meals")).toHaveCount(0);
  await expect(app.id("log-meal-breakfast")).toBeVisible(); // the "+" is back
  await expect(app.id("today-progress-calories")).toContainText("0");
  expect((await app.api("/dashboard")).body.calories).toBe(0);
});

test("5. activity: duration picker, calories scale, remove", async ({ app }) => {
  await app.newUserOnToday("flow5");
  const weight = (await app.api("/me")).body.profile.weight_kg as number;
  const expected = (met: number, minutes: number) => Math.round((met * 3.5 * weight) / 200 * minutes);
  const rows = app.page.locator('[data-testid^="logged-activity-"]');

  await app.id("chip-10-min").click();
  await app.id("log-walk-button").click();
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText(`10 min · ${expected(3.5, 10)} kcal`);

  await app.id("chip-45-min").click();
  await app.id("log-walk-button").click();
  await expect(rows).toHaveCount(2);
  await expect(app.id("logged-activities")).toContainText(`45 min · ${expected(3.5, 45)} kcal`);

  await app.id("chip-30-min").click();
  await app.id("log-strength-button").click();
  await expect(rows).toHaveCount(3);
  await expect(app.id("logged-activities")).toContainText(`30 min · ${expected(5.0, 30)} kcal`);
  await expect(app.id("today-progress-minutes")).toHaveText("85");
  await app.shot("three-activities");

  await app.idStarting("remove-activity-").first().click();
  await expect(rows).toHaveCount(2);
  const dashboard = (await app.api("/dashboard")).body;
  expect(dashboard.activities).toHaveLength(2);
  await expect(app.id("today-progress-minutes")).toHaveText(String(dashboard.activity_minutes));
});

test("6. progress: log a weight, see it in the chart, delete it", async ({ app }) => {
  await app.newUserOnToday("flow6");
  await app.tab("Progress");
  await expect(app.id("progress-screen")).toBeVisible();
  await expect(app.id("weight-entries")).toHaveCount(0);

  await app.id("weight-input").fill("68.5");
  await app.id("log-weight-button").click();
  await expect(app.id("weight-entries")).toContainText("68.5 kg");
  await expect(app.id("weight-chart")).toContainText("68.5");
  await app.shot("weight-logged");
  expect((await app.api("/progress")).body.weights.map((w: { weight_kg: number }) => w.weight_kg)).toEqual([68.5]);

  await app.idStarting("remove-weight-").click();
  await expect(app.id("weight-entries")).toHaveCount(0);
  expect((await app.api("/progress")).body.weights).toEqual([]);
});

test("7. coach: reply, recipe card, and the AI-busy message", async ({ app }) => {
  app.allow(/http 503 POST .*\/coach/, /console\.error Failed to load resource.*503/);
  await app.newUserOnToday("flow7");
  await app.tab("Coach");
  await expect(app.id("coach-screen")).toBeVisible();
  await expect(app.id("coach-wellness-notice")).toBeVisible();

  await app.id("coach-input").fill("Easy dinner idea?");
  await app.id("coach-send-button").click();
  await expect(app.page.getByText("Fake coach: try a balanced plate")).toBeVisible();

  await app.id("coach-input").fill("Share a dinner recipe");
  await app.id("coach-send-button").click();
  await expect(app.page.getByText("Quick vegetable khichdi")).toBeVisible();
  await app.shot("recipe");
  await app.idStarting("recipe-log-").click();
  await expect(app.id("toast-message")).toHaveText("Meal logged");
  expect((await app.api("/dashboard")).body.meals.map((m: { name: string }) => m.name)).toContain("Quick vegetable khichdi");

  await setAi("busy");
  try {
    await app.id("coach-input").fill("Anything else?");
    await app.id("coach-send-button").click();
    await expect(app.id("toast-message")).toHaveText("AI is busy, try again in a minute.", { timeout: 30_000 });
    await app.shot("ai-busy");
  } finally {
    await setAi("ok");
  }
});

test("8. photo logging: upload, confirm form, save as a meal", async ({ app }) => {
  await app.newUserOnToday("flow8");
  await app.id("log-food-photo-button").click();
  await expect(app.id("log-food-screen")).toBeVisible();

  const chooser = app.page.waitForEvent("filechooser");
  await app.id("choose-photo-button").click();
  await (await chooser).setFiles(MEAL_IMAGE);

  await expect(app.id("vision-confirm")).toBeVisible();
  await expect(app.id("vision-field-name")).toHaveValue("Dal tadka with rice");
  await app.shot("confirm");
  await app.id("vision-confirm-button").click();
  await expect(app.id("today-screen")).toBeVisible();
  await expect(app.id("logged-meals")).toContainText("Dal tadka with rice");
  const meal = (await app.api("/dashboard")).body.meals[0];
  expect(meal).toMatchObject({ name: "Dal tadka with rice", calories: 520, source: "photo estimate" });
});

// Words that may legitimately stay English in Telugu mode: product names, units, and data the fake AI or the test
// supplied (meal names, plan text, the person's name).
const ENGLISH_OK = new Set(
  [
    "Wellstride", "kcal", "English", "AI", "Apple", "Health", "Connect", "HealthKit", "min", "kg",
    "E2E", "Tester", "Fake", "coach", "try", "balanced", "plate", "with", "dal", "vegetables", "and", "one", "roti",
    "Moong", "chilla", "Vegetable", "poha", "Idli", "sambar", "Besan", "cheela", "Oats", "upma", "Ragi", "dosa", "Paneer", "paratha",
    "Rajma", "rice", "bowl", "Dal", "palak", "Chole", "salad", "pulao", "raita", "Sambar", "tikka", "wrap", "Millet", "khichdi",
    "Roasted", "chana", "Fruit", "almonds", "Sprouts", "chaat", "Buttermilk", "makhana", "Peanut", "chikki", "Cucumber", "hummus", "yogurt",
    "khichdi", "Tofu", "stir", "fry", "Lauki", "Mixed", "veg", "curry", "soup", "paneer", "Palak", "Bisi", "bele", "bath", "serving",
    "Balanced", "Indian", "meals", "Familiar", "fibre", "protein", "for", "steady", "energy", "Day",
    "Dal", "tadka", "Quick", "vegetable",
  ].map((word) => word.toLowerCase()),
);

test("9. settings: Telugu and back, privacy toggles, reminders, sign out", async ({ app }) => {
  await app.newUserOnToday("flow9");
  await app.id("open-settings-button").click();
  await expect(app.id("settings-screen")).toBeVisible();
  await expect(app.id("settings-screen")).toContainText("Privacy & settings");

  // Privacy toggles and reminders are saved on the server.
  const saved = (url: RegExp, method: string) => app.page.waitForResponse((r) => url.test(r.url()) && r.request().method() === method);
  const analytics = saved(/\/api\/permissions$/, "POST");
  await app.id("toggle-analytics").click();
  expect((await (await analytics).json()).analytics).toBe(true);
  const memory = saved(/\/api\/permissions$/, "POST");
  await app.id("toggle-coach-memory").click();
  expect((await (await memory).json()).coach_memory).toBe(false);
  const reminder = saved(/\/api\/reminders$/, "PUT");
  await app.id("toggle-remind-hydration").click();
  expect((await (await reminder).json()).hydration).toBe(true);
  const permissions = (await app.api("/permissions")).body;
  expect(permissions).toMatchObject({ analytics: true, coach_memory: false });
  expect((await app.api("/reminders")).body.hydration).toBe(true);
  await app.shot("settings-english");

  // Telugu: no raw keys and no stray English on the main screens.
  await app.page.getByText("తెలుగు", { exact: true }).click();
  await expect(app.id("settings-screen")).not.toContainText("Privacy & settings");
  await app.shot("settings-telugu");
  await app.id("settings-close").click();
  await expect(app.id("today-screen")).toBeVisible();
  await app.id("log-meal-breakfast").click();
  await expect(app.id("logged-meals")).toBeVisible();

  const screens: Array<[string, () => Promise<void>]> = [
    ["today", async () => undefined],
    ["plan", async () => app.tab("ప్లాన్")],
    ["coach", async () => app.tab("కోచ్")],
    ["progress", async () => app.tab("పురోగతి")],
  ];
  const problems: string[] = [];
  for (const [name, go] of screens) {
    await go();
    await app.page.waitForTimeout(800);
    await app.shot(`telugu-${name}`);
    const text = await app.text();
    const camel = text.match(/\b[a-z]+[A-Z][A-Za-z]+\b/g) || [];
    if (camel.length) problems.push(`${name}: raw keys ${camel.join(", ")}`);
    const english = (text.match(/[A-Za-z][A-Za-z']{2,}/g) || []).filter((word) => !ENGLISH_OK.has(word.toLowerCase()));
    if (english.length) problems.push(`${name}: English text ${[...new Set(english)].join(", ")}`);
  }
  expect(problems, "raw keys or untranslated English in Telugu mode").toEqual([]);

  // Back to English, then sign out.
  await app.tab("ఈ రోజు");
  await app.id("open-settings-button").click();
  await app.page.getByText("English", { exact: true }).click();
  await expect(app.id("settings-screen")).toContainText("Privacy & settings");
  await app.id("sign-out-button").click();
  await expect(app.id("welcome-screen")).toBeVisible();
});

test("10. rate limit: 11 wrong logins, then a valid user gets back in", async ({ app }) => {
  test.setTimeout(240_000);
  app.allow(/http 401 POST .*\/auth\/login/, /http 429 POST .*\/auth\/login/, /console\.error Failed to load resource.*(401|429)/);
  const valid = uniqueEmail("flow10valid");
  const created = await fetch(`${API}/api/auth/signup`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: valid, password: PASSWORD, accept_terms: true }) });
  expect(created.status).toBe(200);

  await app.open();
  const victim = uniqueEmail("flow10victim");
  let lastError = "";
  for (let attempt = 1; attempt <= 11; attempt++) {
    const response = app.page.waitForResponse((r) => /\/auth\/login$/.test(r.url()));
    await app.signIn(victim, `WrongPass${attempt}`);
    await response;
    lastError = (await app.id("auth-error").innerText()).trim();
    if (attempt <= 3) expect(lastError).toBe("Email or password is incorrect");
  }
  expect(lastError).toMatch(/^Too many attempts\. Please wait \d+ minutes? and try again\.$/);
  await app.shot("too-many-attempts");

  // The limit is a window, not a ban: after it passes a valid user signs in.
  await app.page.waitForTimeout(65_000);
  await app.signIn(valid);
  await expect(app.id("onboarding-screen")).toBeVisible();
  await app.shot("back-in");
});
