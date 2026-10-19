import { expect, lastEmail, PASSWORD, test, uniqueEmail } from "../fixtures";

// Phase 4: forgot password and reset, by typing the code and by opening the emailed link.

const NEW_PASSWORD = "BrandNewPass456";

async function signUpAndOut(app: Parameters<Parameters<typeof test>[2]>[0]["app"], prefix: string) {
  const email = uniqueEmail(prefix);
  await app.open();
  await app.signUp(email);
  await app.completeOnboarding();
  // Password reset only works for a verified email, so verify it first (through the API; flow 16 does it on screen).
  const sent = await lastEmail(email);
  expect((await app.api("/auth/verify-email", { method: "POST", body: { code: /code is: (\d{6})/.exec(sent.text)![1] } })).status).toBe(200);
  await app.id("open-settings-button").click();
  await app.id("sign-out-button").click();
  await expect(app.id("welcome-screen")).toBeVisible();
  return email;
}

const codeIn = (text: string) => /code is: ([A-Z0-9]+)/.exec(text)![1];

test("14. forgot password: request a code, type it, sign in with the new password", async ({ app }) => {
  app.allow(/http 401 POST .*\/auth\/login/, /http 400 POST .*\/auth\/reset-password/, /console\.error Failed to load resource.*(400|401)/);
  const email = await signUpAndOut(app, "forgot");

  await app.id("forgot-password-link").click();
  await expect(app.id("forgot-password-screen")).toBeVisible();
  await app.id("forgot-password-screen").getByTestId("field-email-address").fill(email);
  await app.id("forgot-send-button").click();
  await expect(app.id("reset-password-screen")).toBeVisible();
  await expect(app.id("reset-password-screen").getByTestId("field-email-address")).toHaveValue(email);
  await app.shot("reset-screen");

  const code = codeIn((await lastEmail(email)).text);
  await app.id("field-reset-code").fill("WRONGCODE");
  await app.id("field-new-password").fill(NEW_PASSWORD);
  await app.id("reset-submit-button").click();
  await expect(app.id("reset-error")).toContainText("invalid or has expired");

  await app.id("field-reset-code").fill(code);
  await app.id("reset-submit-button").click();
  await expect(app.id("reset-back-button")).toBeVisible();
  await app.shot("reset-done");
  await app.id("reset-back-button").click();

  await expect(app.id("welcome-screen")).toBeVisible();
  await app.signIn(email, PASSWORD);
  await expect(app.id("auth-error")).toHaveText("Email or password is incorrect");
  await app.signIn(email, NEW_PASSWORD);
  await expect(app.id("today-screen")).toBeVisible();
});

test("15. forgot password: the emailed link opens the reset screen with the code filled in", async ({ app }) => {
  const email = await signUpAndOut(app, "resetlink");
  await app.id("forgot-password-link").click();
  await app.id("forgot-password-screen").getByTestId("field-email-address").fill(email);
  await app.id("forgot-send-button").click();
  await expect(app.id("reset-password-screen")).toBeVisible();

  // The link in the email is wellstride://reset-password?email=..&code=..; on the web build the same route is a URL.
  const message = await lastEmail(email);
  expect(message.text).toContain(`wellstride://reset-password?email=${encodeURIComponent(email)}&code=`);
  const code = codeIn(message.text);
  await app.page.goto(`/reset-password?email=${encodeURIComponent(email)}&code=${code}`);
  await expect(app.id("field-reset-code")).toHaveValue(code);
  await app.id("field-new-password").fill(NEW_PASSWORD);
  await app.id("reset-submit-button").click();
  await expect(app.id("reset-back-button")).toBeVisible();
  await app.id("reset-back-button").click();
  await app.signIn(email, NEW_PASSWORD);
  await expect(app.id("today-screen")).toBeVisible();
});

test("16. verify email: banner on Today, wrong code, right code, banner gone", async ({ app }) => {
  app.allow(/http 400 POST .*\/auth\/verify-email/, /console\.error Failed to load resource.*400/);
  const email = uniqueEmail("verify");
  await app.open();
  await app.signUp(email);
  await app.completeOnboarding();
  await expect(app.id("verify-banner")).toBeVisible();
  await app.shot("banner");
  await app.id("verify-banner").click();
  await expect(app.id("verify-email-screen")).toBeVisible();

  await app.id("field-verification-code").fill("000000");
  await app.id("verify-submit-button").click();
  await expect(app.id("verify-error")).toContainText("invalid or has expired");

  const first = /code is: (\d{6})/.exec((await lastEmail(email)).text)![1];
  await app.id("verify-resend-button").click();
  await expect(app.id("verify-note")).toBeVisible();
  // The resend replaced the first code; wait until the second email is the newest one.
  let code = first;
  for (let attempt = 0; attempt < 40 && code === first; attempt++) {
    code = /code is: (\d{6})/.exec((await lastEmail(email)).text)![1];
    if (code === first) await new Promise((resolve) => setTimeout(resolve, 250));
  }
  await app.id("field-verification-code").fill(code);
  await app.id("verify-submit-button").click();
  await expect(app.id("verify-done-button")).toBeVisible();
  await app.shot("verified");
  await app.id("verify-done-button").click();
  await expect(app.id("today-screen")).toBeVisible();
  await expect(app.id("verify-banner")).toHaveCount(0);
  expect((await app.api("/me")).body.user.email_verified).toBe(true);
});
