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

import type { ProductImageVm } from "@/lib/mappers/products";
import type { GallerySlide } from "@/components/product/ProductGallery";

// ── Product images ────────────────────────────────────────────────────────────

export function makeProductImage(
  overrides?: Partial<ProductImageVm>,
): ProductImageVm {
  return {
    id: 1,
    variants: {
      thumb: "https://example.com/products/gallery/1/thumb.jpg",
      medium: "https://example.com/products/gallery/1/medium.jpg",
      large: "https://example.com/products/gallery/1/large.jpg",
      full: "https://example.com/products/gallery/1/full.jpg",
    },
    alt: "Test Mouse",
    sortOrder: 0,
    ...overrides,
  };
}

export function makeGallerySlide(
  overrides?: Partial<GallerySlide>,
): GallerySlide {
  return {
    id: 1,
    thumb: "https://example.com/products/gallery/1/thumb.jpg",
    main: "https://example.com/products/gallery/1/medium.jpg",
    full: "https://example.com/products/gallery/1/full.jpg",
    alt: "Test Mouse",
    ...overrides,
  };
}

// ── Product ──────────────────────────────────────────────────────────────────

export interface ProductFixture {
  id: string;
  name: string;
  shortDescription?: string;
  description?: string;
  fullDescription?: string;
  price: string;
  currency?: string;
  stockQuantity: number;
  imageUrl?: string;
  primaryImage?: ProductImageVm;
  images?: string[];
  gallery?: ProductImageVm[];
  specs?: Array<{ label: string; value: string }>;
  /** Discounted gross price; present when a promotion applies. */
  discountedPrice?: string;
  /** Original gross price; present when a promotion applies. */
  originalPrice?: string;
  /** Short discount label, e.g. "–10%". */
  discountLabel?: string;
}

export function makeProduct(
  overrides?: Partial<ProductFixture>,
): ProductFixture {
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
  originalUnitPrice?: string;
  discountLabel?: string;
}

export function makeCartItem(
  overrides?: Partial<CartItemFixture>,
): CartItemFixture {
  return {
    productId: "1",
    productName: "Test Mouse",
    unitPrice: "29.99",
    quantity: 1,
    stockQuantity: 10,
    ...overrides,
  };
}

export interface CartOrderDiscountFixture {
  promotionName: string;
  amount: string;
  totalGrossAfter: string;
  totalTaxAfter: string;
}

export interface CartThresholdRewardFixture {
  isUnlocked: boolean;
  promotionName: string;
  remaining: string;
  threshold: string;
}

export interface CartFixture {
  id: string;
  currency?: string;
  items: CartItemFixture[];
  subtotal: string;
  tax?: string;
  total: string;
  /** Phase 4 / Slice 3: auto-applied order-level discount. */
  orderDiscount?: CartOrderDiscountFixture;
  /** Phase 4 / Slice 4: threshold reward progress. */
  thresholdReward?: CartThresholdRewardFixture;
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
  /** Legacy gross unit price */
  unitPrice: string;
  /** Net unit price excl. VAT — Phase 3 */
  unitPriceNet?: string | null;
  /** Gross unit price incl. VAT — Phase 3 */
  unitPriceGross?: string | null;
  /** Per-unit VAT amount — Phase 3 */
  taxAmount?: string | null;
  /** Effective tax rate percentage — Phase 3 */
  taxRate?: string | null;
  /** Legacy gross line total */
  lineTotal: string;
  /** Net line total — Phase 3 */
  lineTotalNet?: string | null;
  /** Gross line total — Phase 3 */
  lineTotalGross?: string | null;
  /** Neutral inline discount note — Phase 3 */
  discountNote?: string | null;
  discount?: { type: "FIXED" | "PERCENT"; value: string } | null;
}

export function makeOrderItem(
  overrides?: Partial<OrderItemFixture>,
): OrderItemFixture {
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
  /** Phase 3 order-level totals */
  subtotalNet?: string | null;
  subtotalGross?: string | null;
  totalTax?: string | null;
  totalDiscount?: string | null;
  currency?: string;
  vatBreakdown?: Array<{
    taxRate: string;
    taxBase: string;
    vatAmount: string;
    totalInclVat: string;
  }> | null;
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
