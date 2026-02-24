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

test.describe("Guest checkout flow", () => {
  test("anonymous user can checkout and sees guest success page", async ({
    page,
  }) => {
    await gotoProducts(page);

    await addProductToCart(page, SELLABLE_ID);

    await openCart(page);
    await expect(
      page.locator(`[data-testid="cart-item-${SELLABLE_ID}"]`),
    ).toBeVisible();

    await checkoutFromCart(page);
    await fillCheckoutForm(page, "guest-e2e@example.com");

    await submitCheckout(page);

    // guest path should go to /guest/checkout/success
    await expect(page).toHaveURL(/\/guest\/checkout\/success/);

    // assert success UI exists
    await expect(
      page.locator("[data-testid='guest-checkout-success']"),
    ).toBeVisible();
  });
});
