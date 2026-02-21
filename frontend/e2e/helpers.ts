import { Page, expect } from "@playwright/test";

export async function gotoProducts(page: Page) {
  // adjust if your products route differs
  await page.goto("/products");
  await expect(
    page.locator("[data-testid^='product-card-']").first(),
  ).toBeVisible();
}

export async function addProductToCart(page: Page, productId: number) {
  await page.locator(`[data-testid="add-to-cart-${productId}"]`).click();
}

export async function openCart(page: Page) {
  await page.locator('[data-testid="nav-cart"]').click();
  await expect(page).toHaveURL(/\/cart/);
}

export async function checkoutFromCart(page: Page) {
  await page.locator('[data-testid="cart-checkout"]').click();
  await expect(page).toHaveURL(/\/checkout/);
}

export async function fillCheckoutForm(page: Page, email: string) {
  await page.fill('input[name="customer_email"]', email);
  await page.fill('input[name="shipping_name"]', "E2E Customer");
  await page.fill('input[name="shipping_address_line1"]', "E2E Street 1");
  await page.fill('input[name="shipping_city"]', "E2E City");
  await page.fill('input[name="shipping_postal_code"]', "12345");
  await page.fill('input[name="shipping_country"]', "CZ");
  await page.fill('input[name="shipping_phone"]', "+420700000000");

  // keep billing_same_as_shipping checked by default
}

export async function submitCheckout(page: Page) {
  await page.locator('[data-testid="checkout-submit"]').click();
}
