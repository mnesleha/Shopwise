import { test, expect } from "@playwright/test";
import {
  gotoProducts,
  addProductToCart,
  openCart,
  checkoutFromCart,
  fillCheckoutForm,
  submitCheckout,
} from "./helpers";

test.describe("Guest checkout flow", () => {
  test("anonymous user can checkout and sees guest success page", async ({
    page,
  }) => {
    await gotoProducts(page);

    // Use a stable seed product ID from your fixtures (E2E_SELLABLE_MOUSE)
    await addProductToCart(page, 1);

    await openCart(page);
    await expect(page.locator('[data-testid="cart-item-1"]')).toBeVisible();

    await checkoutFromCart(page);
    await fillCheckoutForm(page, "guest-e2e@example.com");

    // Wait for checkout API call (adjust endpoint if needed)
    const checkoutResponse = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/cart/checkout/") &&
        r.request().method() === "POST",
    );

    await submitCheckout(page);
    const res = await checkoutResponse;
    expect(res.ok()).toBeTruthy();

    // guest path should go to /guest/checkout/success
    await expect(page).toHaveURL(/\/guest\/checkout\/success/);

    // assert success UI exists
    await expect(
      page.locator("[data-testid='guest-checkout-success']"),
    ).toBeVisible();
  });
});
