import { execFileSync } from "node:child_process";
import path from "node:path";
import { expect, API, PASSWORD, test, uniqueEmail } from "../fixtures";

// Phase 4: the Privacy Policy and Terms are reachable from the sign-up screen and from Settings.

test("11. legal links: sign-up screen and Settings open the policy pages", async ({ app }) => {
  await app.open();
  await app.id("auth-tab-signup").click();
  await expect(app.id("legal-privacy-link")).toBeVisible();
  await app.shot("legal-welcome");

  const popup = app.page.waitForEvent("popup");
  await app.id("legal-privacy-link").click();
  const page = await popup;
  await page.waitForLoadState();
  expect(page.url()).toBe(`${API}/privacy`);
  await expect(page.getByRole("heading", { name: "Privacy Policy" })).toBeVisible();
  await page.close();

  await app.signUp(uniqueEmail("legal"), undefined, "Legal Tester");
  await app.completeOnboarding();
  await app.id("open-settings-button").click();
  await expect(app.id("legal-terms-link")).toBeVisible();
  const terms = app.page.waitForEvent("popup");
  await app.id("legal-terms-link").scrollIntoViewIfNeeded();
  await app.id("legal-terms-link").click();
  const termsPage = await terms;
  await termsPage.waitForLoadState();
  await expect(termsPage.getByRole("heading", { name: "Terms of Use" })).toBeVisible();
});

test("12. consent: sign-up needs the box, and an account without consent is asked once", async ({ app }) => {
  await app.open();
  await app.id("auth-tab-signup").click();
  const email = uniqueEmail("consent");
  await app.id("field-your-name").fill("Consent Tester");
  await app.id("field-email-address").fill(email);
  await app.id("field-password").fill(PASSWORD);
  await expect(app.id("auth-submit-button")).toBeDisabled();
  await app.shot("consent-unchecked");
  await app.id("consent-checkbox").click();
  await expect(app.id("auth-submit-button")).toBeEnabled();
  await app.id("auth-submit-button").click();
  await expect(app.id("onboarding-screen")).toBeVisible();
  expect((await app.api("/me")).body.user.needs_consent).toBe(false);

  // Make this account look like one from before consent existed, then reload: the consent screen comes first.
  const python = process.env.E2E_PYTHON || path.join(__dirname, "..", "..", "backend", ".venv", "Scripts", "python.exe");
  execFileSync(python, ["-I", "-c", "import sys; from pymongo import MongoClient; MongoClient('mongodb://127.0.0.1:27017')[sys.argv[2]].users.update_one({'email': sys.argv[1]}, {'$unset': {'consent_version': '', 'consent_at': ''}})", email, process.env.E2E_DB || "wellstride_e2e"]);
  await app.page.reload();
  await expect(app.id("consent-screen")).toBeVisible();
  await expect(app.id("consent-continue-button")).toBeDisabled();
  await app.shot("consent-existing-account");
  await app.id("consent-checkbox").click();
  await app.id("consent-continue-button").click();
  await expect(app.id("onboarding-screen")).toBeVisible();
  expect((await app.api("/me")).body.user.needs_consent).toBe(false);
});

test("13. delete account: confirm in Settings, signed out, cannot sign in again", async ({ app }) => {
  app.allow(/http 401 POST .*\/auth\/login/, /http 403 DELETE .*\/account/, /console\.error Failed to load resource.*(401|403)/);
  const email = uniqueEmail("delete");
  await app.open();
  await app.signUp(email);
  await app.completeOnboarding();
  await app.id("open-settings-button").click();
  await app.id("delete-account-button").scrollIntoViewIfNeeded();
  await app.id("delete-account-button").click();
  await expect(app.id("delete-account-confirm-button")).toBeDisabled();

  await app.id("field-type-delete-to-confirm").fill("DELETE");
  await app.id("field-password").fill("not-my-password");
  await app.id("delete-account-confirm-button").click();
  await expect(app.id("delete-account-error")).toHaveText("Password is incorrect");
  await app.shot("delete-wrong-password");

  await app.id("field-password").fill(PASSWORD);
  await app.id("delete-account-confirm-button").click();
  await expect(app.id("welcome-screen")).toBeVisible();

  await app.signIn(email);
  await expect(app.id("auth-error")).toHaveText("Email or password is incorrect");
  await app.shot("delete-done");
});
