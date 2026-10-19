import { expect, API, test, uniqueEmail } from "../fixtures";

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
