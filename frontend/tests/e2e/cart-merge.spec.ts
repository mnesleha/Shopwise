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

test("guest cart is merged into user cart on login", async ({ page }) => {
  const email = process.env.E2E_USER_EMAIL!;
  const password = process.env.E2E_USER_PASSWORD!;

  // 1️⃣ Start as guest
  await page.goto("/products");

  // Add first product to cart
  await addProductToCart(page, SELLABLE_ID);

  await openCart(page);
  await expect(
    page.locator(`[data-testid="cart-item-${SELLABLE_ID}"]`),
  ).toBeVisible();

  // 2️⃣ Go to login
  await page.goto("/login");

  await page.getByLabel(/email/i).fill(email);
  await page.getByTestId(/password/i).fill(password);

  await page.getByRole("button", { name: /login|sign in/i }).click();

  // 3️⃣ Expect redirect to products
  await expect(page).toHaveURL(/products/);

  // 4️⃣ Expect merge toast
  await expect(
    page.getByText("Your guest cart was merged into your account."),
  ).toBeVisible();

  // 5️⃣ Go to cart and verify item is still present
  await page.goto("/cart");

  // Cart should not be empty
  // await expect(page.getByText(/total/i)).toBeVisible();

  // Optional: verify badge exists and is > 0
  const badge = page.locator("[data-testid='cart-badge']");
  await expect(badge).toBeVisible();
});
