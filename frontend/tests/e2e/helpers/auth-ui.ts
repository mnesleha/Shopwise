// frontend/tests/e2e/helpers/auth-ui.ts
import { Page, expect } from "@playwright/test";
import { setUserEmailVerified } from "./backend-db";

export async function loginAs(
  page: Page,
  opts: { email: string; password: string; verified?: boolean },
) {
  if (opts.verified !== undefined) {
    setUserEmailVerified(opts.email, opts.verified);
  }

  await page.goto("/login");
  await page.getByLabel(/email/i).fill(opts.email);
  await page.getByTestId(/password/i).fill(opts.password);
  await page.getByRole("button", { name: /sign in|login/i }).click();

  // Assert we're logged in by seeing a known header element or route change
  await expect(page).toHaveURL(/\/products/);
}
