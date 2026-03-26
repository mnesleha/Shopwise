/**
 * ProductGridClient — Type B (Client adapter)
 *
 * Tests the routing and API contracts wired by ProductGridClient.
 * Mocks next/navigation (useRouter + useSearchParams) and the cart API.
 */

import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { makeProduct } from "../helpers/fixtures";
import { createRouterMock } from "../helpers/nextNavigation";
import { addToCart as addToCartTestId } from "../helpers/testIds";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();
const mockSearchParams = { toString: () => "" };

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => mockSearchParams,
  usePathname: () => "/products",
}));

const mockAddCartItem = vi.fn();
vi.mock("@/lib/api/cart", () => ({
  addCartItem: (...args: unknown[]) => mockAddCartItem(...args),
}));

vi.mock("@/components/cart/CartProvider", () => ({
  useCart: () => ({
    refreshCart: vi.fn().mockResolvedValue(undefined),
    count: 0,
    resetCount: vi.fn(),
    orderDiscountApplied: false,
    orderDiscountAmount: null,
  }),
  CartProvider: ({ children }: { children: React.ReactNode }) => children,
}));

const mockToastSuccess = vi.fn();
vi.mock("sonner", () => ({
  toast: { success: (...args: unknown[]) => mockToastSuccess(...args) },
}));

// Import after mocks are set up
import ProductGridClient from "@/components/product/ProductGridClient";

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildProps(
  overrides?: Partial<React.ComponentProps<typeof ProductGridClient>>,
): React.ComponentProps<typeof ProductGridClient> {
  return {
    products: [makeProduct({ id: "1", stockQuantity: 5 })],
    page: 1,
    pageSize: 10,
    totalItems: 1,
    ...overrides,
  };
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  mockAddCartItem.mockResolvedValue(undefined);
  mockToastSuccess.mockClear();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ProductGridClient — routing contracts", () => {
  it("navigates to /products/:id when a product card name is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ProductGridClient
        {...buildProps({
          products: [makeProduct({ id: "42", name: "Clicky Mouse" })],
          totalItems: 1,
        })}
      />,
    );

    // Click the product name (fires onOpenProduct via card click)
    await user.click(screen.getByText("Clicky Mouse"));

    expect(mockRouter.push).toHaveBeenCalledOnce();
    expect(mockRouter.push).toHaveBeenCalledWith("/products/42");
  });

  it("navigates to /products/:id when 'View details' is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ProductGridClient
        {...buildProps({
          products: [makeProduct({ id: "55" })],
          totalItems: 1,
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: /view details/i }));

    expect(mockRouter.push).toHaveBeenCalledOnce();
    expect(mockRouter.push).toHaveBeenCalledWith("/products/55");
  });

  it("navigates to /products?page=2 when Next page is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ProductGridClient
        {...buildProps({ page: 1, pageSize: 10, totalItems: 25 })}
      />,
    );

    await user.click(screen.getByRole("button", { name: /go to next page/i }));

    expect(mockRouter.push).toHaveBeenCalledOnce();
    expect(mockRouter.push).toHaveBeenCalledWith("/products?page=2");
  });

  it("navigates to /products?page=1 when Previous page is clicked from page 2", async () => {
    const user = userEvent.setup();
    render(
      <ProductGridClient
        {...buildProps({ page: 2, pageSize: 10, totalItems: 25 })}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: /go to previous page/i }),
    );

    expect(mockRouter.push).toHaveBeenCalledOnce();
    expect(mockRouter.push).toHaveBeenCalledWith("/products?page=1");
  });

  it("calls addCartItem and does NOT navigate to /cart after add-to-cart", async () => {
    const user = userEvent.setup();
    render(
      <ProductGridClient
        {...buildProps({
          products: [makeProduct({ id: "7", name: "Travel Mug", stockQuantity: 3 })],
          totalItems: 1,
        })}
      />,
    );

    await user.click(screen.getByTestId(addToCartTestId("7")));

    expect(mockAddCartItem).toHaveBeenCalledOnce();
    expect(mockAddCartItem).toHaveBeenCalledWith({ productId: 7, quantity: 1 });
    expect(mockToastSuccess).toHaveBeenCalledWith("Travel Mug added to cart.");
    // User stays on the catalogue — no redirect to /cart.
    await vi.waitFor(() => {
      expect(mockRouter.push).not.toHaveBeenCalledWith("/cart");
    });
  });

  it("does not show an extra order discount toast when no discount is applied", async () => {
    const user = userEvent.setup();
    render(
      <ProductGridClient
        {...buildProps({
          products: [makeProduct({ id: "8", name: "Notebook", stockQuantity: 2 })],
          totalItems: 1,
        })}
      />,
    );

    await user.click(screen.getByTestId(addToCartTestId("8")));

    // orderDiscountApplied stays false in the mock — only the add-to-cart toast is expected.
    await vi.waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledTimes(1);
      expect(mockToastSuccess).toHaveBeenCalledWith("Notebook added to cart.");
    });
  });
});
