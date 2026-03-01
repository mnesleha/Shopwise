import { test, expect } from "@playwright/test";
import { MailpitClient } from "./helpers/mailpit";
import { loginAs } from "./helpers/auth-ui";

test.describe("Email verification flow", () => {
  const mailpit = new MailpitClient(process.env.MAILPIT_BASE_URL);

  test.beforeEach(async () => {
    await mailpit.deleteAllMessages();
  });

  test("orders guard -> resend -> verify via link", async ({ page }) => {
    // const email = `customer_${Date.now()}@example.com`;
    // const password = "customer_test";

    const email = `customer_1@example.com`;
    const password = "customer_1";

    // 1) Register (or login) using your UI helpers...
    // await registerViaUI(page, { email, password });
    await loginAs(page, { email, password, verified: false });

    // 2) Go to /orders: should show gate for unverified
    await page.goto("/orders");
    await expect(page.getByText("Email verification required")).toBeVisible();

    // 3) Click resend
    await page
      .getByRole("button", { name: /resend verification email/i })
      .click();
    await expect(page.getByText(/verification email sent/i)).toBeVisible();

    // 4) Pull email from Mailpit and extract verification link
    const msg = await mailpit.waitForMessage({
      to: email,
      subjectIncludes: "Verify",
    });
    const link = await mailpit.getVerifyEmailLink(
      msg.ID,
      process.env.E2E_BASE_URL,
    );

    // 5) Visit link in browser and expect redirect to /orders after success
    await page.goto(link);
    await expect(page).toHaveURL(/\/orders/);
  });
});
