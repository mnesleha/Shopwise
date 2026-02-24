import { test, expect } from "@playwright/test";
import {
  gotoProducts,
  addProductToCart,
  openCart,
  checkoutFromCart,
  fillCheckoutForm,
  submitCheckout,
} from "./helpers";
import { fixtures } from "./fixtures";

const SELLABLE_ID = fixtures.products.SELLABLE_MOUSE.id;
const E2E_EMAIL = process.env.E2E_USER_EMAIL ?? "admin@example.com";
const E2E_PASSWORD = process.env.E2E_USER_PASSWORD ?? "admin";

test.describe("Authenticated checkout flow", () => {
  // Log in via API and clear any leftover cart item before each test.
  // Prevents dirty state when a previous run failed mid-checkout.
  test.beforeEach(async ({ request }) => {
    await request.post("/api/v1/auth/login/", {
      data: { email: E2E_EMAIL, password: E2E_PASSWORD },
    });
    // Best-effort: ignore 404 if item is not in cart
    await request.delete(`/api/v1/cart/items/${SELLABLE_ID}/`);
  });

  test("user can login and checkout and is redirected to /orders/{id}", async ({
    page,
  }) => {
    // Go to login
    await page.goto("/login");
    await expect(page.locator("[data-testid='login-form']")).toBeVisible();

    await page.fill('input[name="email"]', E2E_EMAIL);
    await page.fill('input[name="password"]', E2E_PASSWORD);

    await page.locator("[data-testid='login-submit']").click();

    // Wait for the app's post-login redirect to /products and auth UI to confirm
    // success — avoids waitForResponse URL-matching issues in WebKit/Firefox.
    await page.waitForURL(/\/products/, { timeout: 15_000 });

    // Header should show logout + email
    await expect(page.locator("[data-testid='nav-logout']")).toBeVisible();
    await expect(page.locator("[data-testid='auth-email']")).toBeVisible();

    // Proceed with purchase
    await gotoProducts(page);
    await addProductToCart(page, SELLABLE_ID);

    await openCart(page);
    await checkoutFromCart(page);

    await fillCheckoutForm(page, E2E_EMAIL);

    await submitCheckout(page);

    // Auth flow should redirect to /orders/{id}
    await expect(page).toHaveURL(/\/orders\/\d+/);

    // Assert order detail UI loads
    await expect(page.locator("[data-testid='order-title']")).toBeVisible();
    await expect(page.locator("[data-testid='order-status']")).toBeVisible();
  });
});
