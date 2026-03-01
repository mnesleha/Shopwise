import { test, expect } from "@playwright/test";
import { MailpitClient } from "./helpers/mailpit";

test("register -> toasts -> products -> verify via email link", async ({
  page,
}) => {
  const mailpit = new MailpitClient();
  await mailpit.deleteAllMessages();

  const email = `e2e_${Date.now()}@example.com`;
  const password = "e2e_password";

  await page.goto("/register");

  // Adjust selectors to your RegisterForm fields
  await page.getByLabel(/email/i).fill(email);
  await page.getByTestId(/password/i).fill(password);
  await page
    .getByRole("button", { name: /create account|sign up|register/i })
    .click();

  // Toasts (exact text depends on your implementation)
  await expect(page.getByText(/account created and signed in/i)).toBeVisible();
  await expect(page.getByText(/verify your email/i)).toBeVisible();

  // Redirect destination per your decision
  await expect(page).toHaveURL(/\/products/);

  const msg = await mailpit.waitForMessage({
    to: email,
    subjectIncludes: "Verify",
  });
  const link = await mailpit.getVerifyEmailLink(
    msg.ID,
    process.env.E2E_BASE_URL,
  );

  await page.goto(link);

  // After verify you may redirect to /orders (recommended) or /products.
  await expect(page).toHaveURL(/\/(orders|products)/);
});
