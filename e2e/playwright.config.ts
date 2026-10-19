import { defineConfig } from "@playwright/test";

const WEB_PORT = process.env.E2E_WEB_PORT || "8102";

// Uses the Microsoft Edge that ships with Windows, so no browser download is needed. To use Playwright's own Chromium
// instead (for example on CI), run `npm run install-browser` once and set E2E_BROWSER=chromium.
const channel = process.env.E2E_BROWSER === "chromium" ? undefined : "msedge";

export default defineConfig({
  testDir: "./tests",
  outputDir: "./test-results",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1, // one backend, one database, one rate limiter: tests run one after another
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  globalSetup: "./global-setup.ts",
  globalTeardown: "./global-teardown.ts",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    channel,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    // The app is a phone app first: 390x844.
    { name: "phone", use: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: false, hasTouch: false } },
    // One desktop pass over the flows tagged @desktop.
    { name: "desktop", grep: /@desktop/, use: { viewport: { width: 1280, height: 800 } } },
  ],
});
