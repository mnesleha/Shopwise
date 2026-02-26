/**
 * Centralised data-testid constants.
 *
 * Import these in unit tests instead of using raw string literals.
 * They mirror the testids used in Playwright E2E tests.
 *
 * Naming convention: <component-kebab>__<element>
 */

// ── Auth ─────────────────────────────────────────────────────────────────────
export const LOGIN_FORM = "login-form";
export const LOGIN_SUBMIT = "login-submit";

// ── Cart ─────────────────────────────────────────────────────────────────────
export const CART_CHECKOUT_BUTTON = "cart-checkout";

/** Pass productId to get the cart item testid */
export const cartItem = (productId: string | number) =>
  `cart-item-${productId}`;

// ── Checkout ──────────────────────────────────────────────────────────────────
export const CHECKOUT_CONTINUE = "checkout-continue";
export const CHECKOUT_SUBMIT = "checkout-submit";
export const GUEST_CHECKOUT_SUCCESS = "guest-checkout-success";

// ── Product ──────────────────────────────────────────────────────────────────
export const addToCart = (productId: string | number) =>
  `add-to-cart-${productId}`;
export const productCard = (productId: string | number) =>
  `product-card-${productId}`;

// ── Order ────────────────────────────────────────────────────────────────────
export const ORDER_TITLE = "order-title";
export const ORDER_STATUS = "order-status";
