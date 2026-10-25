import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type App } from "../fixtures";

// Design run: the shell, tokens, fonts and dark mode, looked at in three sizes, light and dark, English and Telugu.
// Screenshots go to e2e/screenshots/design/<name>-<size>-<scheme>-<language>.png and are reviewed by eye.

const SIZES = { phone: { width: 390, height: 844 }, tablet: { width: 820, height: 1180 }, desktop: { width: 1440, height: 900 } } as const;
const SCHEMES = ["light", "dark"] as const;
const DIR = path.join(__dirname, "..", "screenshots", "design");

async function snapshot(app: App, name: string, size: keyof typeof SIZES, scheme: string, lang: string) {
  mkdirSync(DIR, { recursive: true });
  await app.page.screenshot({ path: path.join(DIR, `${name}-${size}-${scheme}-${lang}.png`), fullPage: false });
}

async function setLanguage(app: App, lang: "en" | "te") {
  await app.page.evaluate((value) => window.localStorage.setItem("nutrimitra.lang", JSON.stringify(value)), lang);
  await app.page.reload();
  await expect(app.id("today-screen")).toBeVisible();
}

const background = (app: App) => app.page.evaluate(() => getComputedStyle(document.body).backgroundColor);

test("design: the shell is a bottom bar on phone and tablet and a sidebar on a wide screen", async ({ app }) => {
  await app.newUserOnToday("designshell");
  await app.page.setViewportSize(SIZES.phone);
  await expect(app.id("tab-bar")).toBeVisible();
  await expect(app.id("sidebar")).toHaveCount(0);
  await app.page.setViewportSize(SIZES.tablet);
  await expect(app.id("tab-bar")).toBeVisible();
  await app.page.setViewportSize(SIZES.desktop);
  await expect(app.id("sidebar")).toBeVisible();
  await expect(app.id("tab-bar")).toHaveCount(0);
  for (const id of ["nav-index", "nav-plan", "nav-coach", "nav-progress", "nav-kitchen", "nav-settings"]) await expect(app.id(id)).toBeVisible();
  // The four tabs still work from the sidebar, and keep their accessible names.
  await app.tab("Plan");
  await expect(app.id("plan-screen")).toBeVisible();
  await app.tab("Today");
  await expect(app.id("today-screen")).toBeVisible();
  // Nothing hugs the left edge: the page content starts to the right of the sidebar (264 px).
  const box = await app.id("today-screen").boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(260);
});

test("design: settings opens as a centred dialog on a wide screen and as a full screen on a phone", async ({ app }) => {
  await app.newUserOnToday("designdialog");
  await app.page.setViewportSize(SIZES.desktop);
  await app.id("nav-settings").click();
  await expect(app.id("settings-screen")).toBeVisible();
  const dialog = await app.id("settings-screen").boundingBox();
  expect(dialog!.width).toBeLessThanOrEqual(780);
  expect(dialog!.x).toBeGreaterThan(300);
  await snapshot(app, "settings-dialog", "desktop", "light", "en");
  await app.id("settings-close").click();
  await expect(app.id("today-screen")).toBeVisible();
  await app.page.setViewportSize(SIZES.phone);
  await app.id("open-settings-button").click();
  const full = await app.id("settings-screen").boundingBox();
  expect(full!.width).toBeGreaterThanOrEqual(385);
});

test("design: dark mode follows the device, and Settings can override it", async ({ app }) => {
  await app.page.emulateMedia({ colorScheme: "dark" });
  await app.newUserOnToday("designdark");
  expect(await background(app)).toBe("rgb(17, 24, 21)");
  await app.id("open-settings-button").click();
  await app.id("theme-picker-light").click();
  await app.id("settings-close").click();
  await expect.poll(() => background(app)).toBe("rgb(251, 248, 242)");
  // The choice is remembered across a reload.
  await app.page.reload();
  await expect(app.id("today-screen")).toBeVisible();
  expect(await background(app)).toBe("rgb(251, 248, 242)");
  await app.id("open-settings-button").click();
  await app.id("theme-picker-system").click();
  await app.id("settings-close").click();
  await expect.poll(() => background(app)).toBe("rgb(17, 24, 21)");
});

test("design: fonts load (Plus Jakarta Sans for English, Noto Sans Telugu for Telugu)", async ({ app }) => {
  await app.newUserOnToday("designfonts");
  const families = await app.page.evaluate(async () => {
    await document.fonts.ready;
    return Array.from(document.fonts).filter((face) => face.status === "loaded").map((face) => face.family.replace(/['"]/g, ""));
  });
  expect(families.some((family) => family.startsWith("PlusJakartaSans"))).toBe(true);
  await setLanguage(app, "te");
  const telugu = await app.page.evaluate(async () => {
    await document.fonts.ready;
    return Array.from(document.fonts).filter((face) => face.status === "loaded").map((face) => face.family.replace(/['"]/g, ""));
  });
  expect(telugu.some((family) => family.startsWith("NotoSansTelugu"))).toBe(true);
});

test("design: screenshots of Today at three sizes, light and dark, English and Telugu", async ({ app }) => {
  await app.newUserOnToday("designshots");
  for (const lang of ["en", "te"] as const) {
    await setLanguage(app, lang);
    for (const scheme of SCHEMES) {
      await app.page.emulateMedia({ colorScheme: scheme });
      for (const [size, viewport] of Object.entries(SIZES) as [keyof typeof SIZES, { width: number; height: number }][]) {
        await app.page.setViewportSize(viewport);
        await expect(app.id("today-screen")).toBeVisible();
        await expect.poll(() => background(app)).toBe(scheme === "dark" ? "rgb(17, 24, 21)" : "rgb(251, 248, 242)");
        await snapshot(app, "today", size, scheme, lang);
      }
    }
  }
});
