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
export const CART_THRESHOLD_REWARD = "threshold-reward-banner";

/** Pass productId to get the cart item testid */
export const cartItem = (productId: string | number) =>
  `cart-item-${productId}`;

// ── Checkout ──────────────────────────────────────────────────────────────────
export const CHECKOUT_CONTINUE = "checkout-continue";
export const CHECKOUT_BACK = "checkout-back";
export const CHECKOUT_SUBMIT = "checkout-submit";
export const GUEST_CHECKOUT_SUCCESS = "guest-checkout-success";

// Price-change banner (shown after WARNING-severity checkout response)
export const CHECKOUT_PRICE_CHANGE_BANNER = "checkout-price-change-banner";
export const CHECKOUT_PRICE_CHANGE_CONTINUE = "checkout-price-change-continue";
export const CHECKOUT_PRICE_CHANGE_BACK = "checkout-price-change-back";

// ── Product ──────────────────────────────────────────────────────────────────
export const addToCart = (productId: string | number) =>
  `add-to-cart-${productId}`;
export const productCard = (productId: string | number) =>
  `product-card-${productId}`;

// ── Order ────────────────────────────────────────────────────────────────────
export const ORDER_TITLE = "order-title";
export const ORDER_STATUS = "order-status";
export const ORDER_ITEMS_TABLE = "order-items-table";
export const VAT_BREAKDOWN = "vat-breakdown";
export const ORDER_SUMMARY = "order-summary";
export const ITEM_DISCOUNT_NOTE = "item-discount-note";
export const ORDER_DISCOUNT_NOTE = "order-discount-note";
export const ORDER_DISCOUNT_ROW = "order-discount-row";
export const VAT_BREAKDOWN_ORDER_DISCOUNT_NOTE = "vat-breakdown-order-discount-note";
/** Returns the testid for a specific VAT rate row, e.g. vatBreakdownRow("10.00") */
export const vatBreakdownRow = (rate: string) => `vat-row-${rate}`;
