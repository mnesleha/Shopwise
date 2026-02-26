/**
 * Test data factories.
 *
 * Each factory returns a minimal, valid object. Override individual fields by
 * spreading the result:
 *   makeProduct({ stockQuantity: 0 })  // out-of-stock product
 *
 * These are isolated from the E2E fixtures in tests/e2e/fixtures.ts on purpose:
 * unit tests must not depend on backend seed state.
 */

// ── Product ──────────────────────────────────────────────────────────────────

export interface ProductFixture {
  id: string;
  name: string;
  shortDescription?: string;
  description?: string;
  price: string;
  currency?: string;
  stockQuantity: number;
  imageUrl?: string;
  images?: string[];
  specs?: Array<{ label: string; value: string }>;
}

export function makeProduct(overrides?: Partial<ProductFixture>): ProductFixture {
  return {
    id: "1",
    name: "Test Mouse",
    shortDescription: "A reliable office mouse",
    description: "Full description of the test mouse.",
    price: "29.99",
    currency: "USD",
    stockQuantity: 10,
    ...overrides,
  };
}

// ── Cart ─────────────────────────────────────────────────────────────────────

export interface CartItemFixture {
  productId: string;
  productName: string;
  productUrl?: string;
  shortDescription?: string;
  unitPrice: string;
  quantity: number;
  stockQuantity?: number;
  imageUrl?: string;
}

export function makeCartItem(overrides?: Partial<CartItemFixture>): CartItemFixture {
  return {
    productId: "1",
    productName: "Test Mouse",
    unitPrice: "29.99",
    quantity: 1,
    stockQuantity: 10,
    ...overrides,
  };
}

export interface CartFixture {
  id: string;
  currency?: string;
  items: CartItemFixture[];
  subtotal: string;
  tax?: string;
  total: string;
}

export function makeCart(overrides?: Partial<CartFixture>): CartFixture {
  return {
    id: "cart-1",
    currency: "USD",
    items: [makeCartItem()],
    subtotal: "29.99",
    total: "29.99",
    ...overrides,
  };
}

// ── OrderViewModel ────────────────────────────────────────────────────────────

export interface OrderItemFixture {
  id: string;
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: string;
  lineTotal: string;
  discount?: { type: "FIXED" | "PERCENT"; value: string } | null;
}

export function makeOrderItem(overrides?: Partial<OrderItemFixture>): OrderItemFixture {
  return {
    id: "item-1",
    productId: "1",
    productName: "Test Mouse",
    quantity: 2,
    unitPrice: "29.99",
    lineTotal: "59.98",
    discount: null,
    ...overrides,
  };
}

export interface OrderViewModelFixture {
  id: string;
  orderNumber: string;
  status: string;
  createdAt?: string;
  supplier: {
    name: string;
    addressLine1: string;
    city: string;
    postalCode: string;
    country: string;
  };
  customer: {
    name: string;
    addressLine1: string;
    city: string;
    postalCode: string;
    country: string;
    email?: string;
  };
  shippingMethod?: string;
  paymentMethod?: string;
  items: OrderItemFixture[];
  subtotal?: string;
  total: string;
}

export function makeOrderViewModel(
  overrides?: Partial<OrderViewModelFixture>,
): OrderViewModelFixture {
  return {
    id: "order-42",
    orderNumber: "OBJ25000042",
    status: "CREATED",
    createdAt: "February 25, 2026",
    supplier: {
      name: "Shopwise s.r.o.",
      addressLine1: "Main Street 1",
      city: "Prague",
      postalCode: "11000",
      country: "CZ",
    },
    customer: {
      name: "Jane Test",
      addressLine1: "Test Street 10",
      city: "Brno",
      postalCode: "60200",
      country: "CZ",
      email: "jane@example.com",
    },
    items: [makeOrderItem()],
    subtotal: "59.98",
    total: "59.98",
    ...overrides,
  };
}
