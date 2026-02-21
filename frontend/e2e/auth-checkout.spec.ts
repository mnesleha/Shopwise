import { test, expect } from "@playwright/test";
import {
  gotoProducts,
  addProductToCart,
  openCart,
  checkoutFromCart,
  fillCheckoutForm,
  submitCheckout,
} from "./helpers";

test.describe("Authenticated checkout flow", () => {
  test("user can login and checkout and is redirected to /orders/{id}", async ({
    page,
  }) => {
    // Go to login
    await page.goto("/login");
    await expect(page.locator("[data-testid='login-form']")).toBeVisible();

    await page.fill(
      'input[name="email"]',
      process.env.E2E_USER_EMAIL ?? "admin@example.com",
    );
    await page.fill(
      'input[name="password"]',
      process.env.E2E_USER_PASSWORD ?? "Passw0rd!123",
    );

    const loginResp = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/auth/login/") &&
        r.request().method() === "POST",
    );

    await page.locator("[data-testid='login-submit']").click();
    const lr = await loginResp;
    expect(lr.ok()).toBeTruthy();

    // Header should show logout + email
    await expect(page.locator("[data-testid='nav-logout']")).toBeVisible();
    await expect(page.locator("[data-testid='auth-email']")).toBeVisible();

    // Proceed with purchase
    await gotoProducts(page);
    await addProductToCart(page, 1);

    await openCart(page);
    await checkoutFromCart(page);

    // For auth checkout, customer_email might be prefilled or required – fill anyway
    await fillCheckoutForm(
      page,
      process.env.E2E_USER_EMAIL ?? "admin@example.com",
    );

    const checkoutResponse = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/cart/checkout/") &&
        r.request().method() === "POST",
    );

    await submitCheckout(page);
    const res = await checkoutResponse;
    expect(res.ok()).toBeTruthy();

    // Auth flow should redirect to /orders/{id}
    await expect(page).toHaveURL(/\/orders\/\d+/);

    // Assert order detail UI loads
    await expect(page.locator("[data-testid='order-title']")).toBeVisible();
    await expect(page.locator("[data-testid='order-status']")).toBeVisible();
  });
});
