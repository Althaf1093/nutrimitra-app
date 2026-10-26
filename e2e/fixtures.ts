import { expect, test as base, type Page, type TestInfo } from "@playwright/test";
import path from "node:path";
import { mkdirSync } from "node:fs";

export const API = process.env.E2E_API_URL || "http://localhost:8101";
export const AI = `http://127.0.0.1:${process.env.E2E_AI_PORT || "8103"}`;
export const PASSWORD = "StrongPass123";
export const MEAL_IMAGE = path.join(__dirname, "fixtures", "meal.jpg");

type Issue = { kind: string; text: string };

export const uniqueEmail = (prefix = "e2e") => `${prefix}.${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}@example.com`;

// The newest email the backend sent to an address (read from the fake of Resend), waiting a few seconds for it to arrive.
export async function lastEmail(to: string): Promise<{ subject: string; text: string }> {
  for (let attempt = 0; attempt < 40; attempt++) {
    const sent = (await (await fetch(`${AI}/__emails?to=${encodeURIComponent(to)}`)).json()) as { subject: string; text: string }[];
    if (sent.length) return sent[sent.length - 1];
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`no email was sent to ${to}`);
}

// Switches the fake AI between answering ("ok") and rate limiting every call ("busy").
export async function setAi(mode: "ok" | "busy") {
  const response = await fetch(`${AI}/__mode`, { method: "POST", body: JSON.stringify({ mode }) });
  expect(response.ok).toBeTruthy();
}

// The test backend allows 10 sign-ups a minute per address (flow 10 relies on that limit). The run has more flows than that
// now, so a sign-up waits when the last minute is already nearly full.
const signupTimes: number[] = [];
async function paceSignups() {
  const recent = signupTimes.filter((time) => Date.now() - time < 61_000);
  signupTimes.length = 0;
  signupTimes.push(...recent);
  if (recent.length >= 8) await new Promise((resolve) => setTimeout(resolve, 61_500 - (Date.now() - recent[0])));
  signupTimes.push(Date.now());
}

export class App {
  readonly issues: Issue[] = [];
  private allowed: RegExp[] = [];

  constructor(readonly page: Page, private readonly info: TestInfo) {
    page.on("console", (message) => {
      if (message.type() === "error" || message.type() === "warning") this.issues.push({ kind: `console.${message.type()}`, text: message.text() });
    });
    page.on("pageerror", (error) => this.issues.push({ kind: "pageerror", text: String(error) }));
    page.on("requestfailed", (request) => this.issues.push({ kind: "requestfailed", text: `${request.failure()?.errorText} ${request.method()} ${request.url()}` }));
    page.on("response", (response) => {
      if (response.status() >= 400) this.issues.push({ kind: "http", text: `${response.status()} ${response.request().method()} ${response.url()}` });
    });
  }

  /** Declare an error this test expects (for example a 401 for a wrong password). Anything else fails the test. */
  allow(...patterns: RegExp[]) {
    this.allowed.push(...patterns);
  }

  unexpectedIssues() {
    return this.issues.filter((issue) => !this.allowed.some((pattern) => pattern.test(`${issue.kind} ${issue.text}`)));
  }

  async shot(name: string) {
    const dir = path.join(__dirname, "screenshots", this.info.project.name);
    mkdirSync(dir, { recursive: true });
    await this.page.screenshot({ path: path.join(dir, `${this.info.title.match(/^\w+/)?.[0] ?? "flow"}-${name}.png`), fullPage: false });
  }

  id(testId: string) {
    return this.page.getByTestId(testId);
  }

  /** Locator for the first element whose test id starts with a prefix (ids that end in a database id). */
  idStarting(prefix: string) {
    return this.page.locator(`[data-testid^="${prefix}"]`).first();
  }

  async open() {
    await this.page.goto("/");
    await expect(this.id("welcome-screen")).toBeVisible();
  }

  /** On a phone the welcome screen shows Get started / I have an account first; this opens the form in the wanted mode. */
  async openAuth(mode: "signin" | "signup") {
    const entry = this.id(mode === "signup" ? "get-started-button" : "have-account-button");
    if (await entry.isVisible()) await entry.click();
    await this.id(`auth-tab-${mode}`).click();
  }

  async signUp(email: string, password = PASSWORD, name = "E2E Tester") {
    await paceSignups();
    await this.openAuth("signup");
    await this.id("field-your-name").fill(name);
    await this.id("field-email-address").fill(email);
    await this.id("field-password").fill(password);
    await this.id("consent-checkbox").click();
    await this.id("auth-submit-button").click();
  }

  async signIn(email: string, password = PASSWORD) {
    await this.openAuth("signin");
    await this.id("field-email-address").fill(email);
    await this.id("field-password").fill(password);
    await this.id("auth-submit-button").click();
  }

  /** Walks the four onboarding steps with the default (vegetarian, 30 year old) profile and lands on Today. */
  async completeOnboarding(age = "30") {
    await expect(this.id("onboarding-screen")).toBeVisible();
    await this.id("field-age").fill(age);
    await this.id("onboarding-next-button").click();
    await this.id("onboarding-next-button").click();
    await this.id("onboarding-next-button").click();
    await expect(this.id("kitchen-editor")).toBeVisible();
    await this.id("onboarding-next-button").click(); // nothing picked: the kitchen is skipped
    await expect(this.id("today-screen")).toBeVisible();
  }

  /** Onboarding with the default profile and a kitchen of the given ingredient ids (vegetarian unless `diet` says otherwise). */
  async onboardWithKitchen(items: string[], options: { diet?: string } = {}) {
    await expect(this.id("onboarding-screen")).toBeVisible();
    await this.id("field-age").fill("30");
    await this.id("onboarding-next-button").click();
    if (options.diet) {
      await this.id("chip-vegetarian").click();
      await this.id(`chip-${options.diet}`).click();
    }
    await this.id("onboarding-next-button").click();
    await this.id("onboarding-next-button").click();
    await expect(this.id("kitchen-editor")).toBeVisible();
    for (const id of items) await this.id(`chip-${id}`).click();
    await this.id("onboarding-next-button").click();
    await expect(this.id("today-screen")).toBeVisible();
  }

  async newUserOnToday(prefix = "e2e") {
    const email = uniqueEmail(prefix);
    await this.open();
    await this.signUp(email);
    await this.completeOnboarding();
    return email;
  }

  /** The sign-in token the app saved in the browser (web keeps it in localStorage). */
  async token(): Promise<string> {
    // The app stores values JSON-encoded, so the token is saved with surrounding quotes.
    const token = await this.page.evaluate(() => {
      const raw = Object.values(window.localStorage).find((value) => /^"?eyJ/.test(value)) || "";
      return raw.replace(/^"|"$/g, "");
    });
    expect(token, "a saved sign-in token").not.toBe("");
    return token;
  }

  /** Calls the backend as the signed-in user, to check what the server actually stored. */
  async api(pathname: string, init: { method?: string; body?: unknown } = {}) {
    const response = await fetch(`${API}/api${pathname}`, {
      method: init.method || "GET",
      headers: { Authorization: `Bearer ${await this.token()}`, "Content-Type": "application/json" },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
    return { status: response.status, body: await response.json().catch(() => ({})) as any };
  }

  async tab(name: string) {
    await this.page.getByRole("tab", { name }).click();
  }

  async text() {
    return (await this.page.locator("body").innerText()).replace(/\s+/g, " ");
  }
}

export const test = base.extend<{ app: App }>({
  app: async ({ page }, use, info) => {
    const app = new App(page, info);
    await use(app);
    const unexpected = app.unexpectedIssues();
    expect(unexpected, "unexpected console errors, page errors or failed requests").toEqual([]);
  },
});

export { expect };
