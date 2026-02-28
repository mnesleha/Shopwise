import { test, expect } from "@playwright/test";
import { adminCancelOrder } from "./admin";
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

test.describe("Authenticated order cancellation", () => {
  // Log in via API and clear any leftover cart item before each test.
  // Prevents dirty state when a previous run failed mid-checkout.
  test.beforeEach(async ({ request }) => {
    await request.post("/api/v1/auth/login/", {
      data: { email: E2E_EMAIL, password: E2E_PASSWORD },
    });
    // Best-effort: ignore 404 if item is not in cart
    await request.delete(`/api/v1/cart/items/${SELLABLE_ID}/`);
  });

  test("stale UI: admin cancels order while customer has cancel dialog open", async ({
    page,
  }) => {
    // Provide an existing CREATED order id for the logged-in customer.
    // Easiest: set via env var from CI/local.
    const orderId = process.env.E2E_ORDER_ID;
    let createdOrderId: number | null = null;

    if (!orderId) throw new Error("E2E_ORDER_ID is required for this test");

    await page.goto("/login");

    await page.fill('input[name="email"]', E2E_EMAIL);
    await page.fill('input[name="password"]', E2E_PASSWORD);

    await page.locator("[data-testid='login-submit']").click();

    // Wait for the app's post-login redirect to /products and auth UI to confirm
    // success — avoids waitForResponse URL-matching issues in WebKit/Firefox.
    await page.waitForURL(/\/products/, { timeout: 15_000 });

    // Proceed with purchase
    await gotoProducts(page);
    await addProductToCart(page, SELLABLE_ID);

    await openCart(page);
    await checkoutFromCart(page);

    await fillCheckoutForm(page, E2E_EMAIL);

    page.on("response", async (res) => {
      if (
        res.request().method() === "POST" &&
        res.url().includes("/api/v1/") &&
        res.url().includes("/checkout/") &&
        res.ok()
      ) {
        const data = await res.json().catch(() => null);
        if (data?.id) createdOrderId = data.id;
      }
    });

    await submitCheckout(page);

    // Open cancel dialog
    await page.getByRole("button", { name: "Cancel order" }).click();
    await expect(page.getByText("Cancel this order?")).toBeVisible();

    // Simulate admin cancellation in the background
    await adminCancelOrder(Number(createdOrderId));

    // Customer tries to cancel, backend should return 409 INVALID_ORDER_STATE
    await page.getByRole("button", { name: "Cancel order" }).click();

    // Dialog should close
    await expect(page.getByText("Cancel this order?")).toBeHidden();

    // Toast should be shown (message comes from backend)
    await expect(
      page.getByText("Order is not in a state that allows this operation."),
    ).toBeVisible();

    // After refresh revalidation, cancel button should disappear
    await expect(
      page.getByRole("button", { name: "Cancel order" }),
    ).toBeHidden();

    // Optional: verify status is cancelled somewhere in UI
    // (Adjust selector to your badge text)
    await expect(page.getByText(/cancelled/i)).toBeVisible();
  });
});
