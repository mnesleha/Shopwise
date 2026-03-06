/**
 * Cart page — stock-adjustment banner + item highlight (sessionStorage flow)
 *
 * Contracts guarded:
 * A) When sessionStorage["cartMergeWarnings"] contains valid warnings,
 *    CartDetailClient shows the adjustment banner and a badge on the affected item.
 * B) The sessionStorage key is deleted after reading (one-time display).
 * C) When sessionStorage key is absent, no banner is rendered.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as React from "react";
import { screen, waitFor } from "@testing-library/react";
import CartDetailClient from "@/components/cart/CartDetailClient";
import { renderWithProviders } from "../helpers/render";
import { makeCartItem } from "../helpers/fixtures";
import { createRouterMock } from "../helpers/nextNavigation";
import type { CartVm } from "@/lib/mappers/cart";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/cart",
}));

vi.mock("@/lib/api/cart", () => ({
  deleteCartItem: vi.fn().mockResolvedValue({}),
  getCart: vi
    .fn()
    .mockResolvedValue({ id: "1", items: [], subtotal: "0.00", total: "0.00" }),
  updateCartItemQuantity: vi.fn().mockResolvedValue({}),
}));

vi.mock("@/lib/mappers/cart", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/mappers/cart")>();
  return {
    ...actual,
    mapCartToVm: vi.fn((dto) => ({
      id: dto.id,
      items: [],
      subtotal: "0.00",
      total: "0.00",
    })),
  };
});

vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => ({ isAuthenticated: true, email: "user@example.com" }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/components/cart/CartProvider", () => ({
  useCart: () => ({ refreshCart: vi.fn(), count: 0, resetCount: vi.fn() }),
  CartProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Build a minimal CartVm that contains one item for the given productId. */
function makeCartVm(productId: string, quantity = 1): CartVm {
  return {
    id: "1",
    currency: "USD",
    items: [
      makeCartItem({
        productId,
        productName: `Product ${productId}`,
        quantity,
      }),
    ],
    subtotal: "9.99",
    total: "9.99",
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CartDetailClient — merge-warnings sessionStorage flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it("shows the adjustment banner when sessionStorage has warnings", async () => {
    const warnings = [
      { code: "STOCK_ADJUSTED", product_id: 5, requested: 3, applied: 1 },
    ];
    sessionStorage.setItem("cartMergeWarnings", JSON.stringify(warnings));

    renderWithProviders(
      <CartDetailClient initialCartVm={makeCartVm("5", 1)} />,
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("cart-merge-adjustment-banner"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Stock adjustments applied")).toBeInTheDocument();
  });

  it("shows an 'Updated' badge on the adjusted item row", async () => {
    const warnings = [
      { code: "STOCK_ADJUSTED", product_id: 5, requested: 3, applied: 1 },
    ];
    sessionStorage.setItem("cartMergeWarnings", JSON.stringify(warnings));

    renderWithProviders(
      <CartDetailClient initialCartVm={makeCartVm("5", 1)} />,
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("cart-item-adjusted-badge"),
      ).toBeInTheDocument();
    });
    // Badge shows "Updated"; the requested→applied detail is in the banner list.
    expect(screen.getByTestId("cart-item-adjusted-badge")).toHaveTextContent(
      "Updated",
    );
  });

  it("deletes the sessionStorage key after displaying warnings", async () => {
    const warnings = [
      { code: "STOCK_ADJUSTED", product_id: 5, requested: 3, applied: 1 },
    ];
    sessionStorage.setItem("cartMergeWarnings", JSON.stringify(warnings));

    renderWithProviders(
      <CartDetailClient initialCartVm={makeCartVm("5", 1)} />,
    );

    // Wait for useEffect to have run
    await waitFor(() => {
      expect(
        screen.getByTestId("cart-merge-adjustment-banner"),
      ).toBeInTheDocument();
    });

    // Key must be removed after first render
    expect(sessionStorage.getItem("cartMergeWarnings")).toBeNull();
  });

  it("does not show the banner when sessionStorage key is absent", async () => {
    // Ensure key is not present
    sessionStorage.removeItem("cartMergeWarnings");

    renderWithProviders(
      <CartDetailClient initialCartVm={makeCartVm("5", 1)} />,
    );

    // Allow effects to settle
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(
      screen.queryByTestId("cart-merge-adjustment-banner"),
    ).not.toBeInTheDocument();
  });

  it("handles malformed sessionStorage value gracefully (no banner)", async () => {
    sessionStorage.setItem("cartMergeWarnings", "not-valid-json{{{");

    renderWithProviders(
      <CartDetailClient initialCartVm={makeCartVm("5", 1)} />,
    );

    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(
      screen.queryByTestId("cart-merge-adjustment-banner"),
    ).not.toBeInTheDocument();
    // Key should still have been removed
    expect(sessionStorage.getItem("cartMergeWarnings")).toBeNull();
  });
});
