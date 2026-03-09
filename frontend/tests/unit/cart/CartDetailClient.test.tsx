/**
 * CartDetailClient — Type B (Client adapter)
 *
 * Contract guarded:
 * - "Proceed to checkout" navigates to /checkout when user is authenticated
 * - "Proceed to checkout" navigates to /guest/checkout when user is not authenticated
 * - "Continue shopping" navigates to /products
 * - onClearCart calls clearCart() once (not deleteCartItem in a loop)
 * - refresh (getCart) runs after onClearCart succeeds
 * - onIncreaseQty / onDecreaseQty call updateCartItemQuantity (PATCH-backed)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import * as React from "react";
import userEvent from "@testing-library/user-event";
import CartDetailClient from "@/components/cart/CartDetailClient";
import { renderWithProviders } from "../helpers/render";
import { makeCart, makeCartItem } from "../helpers/fixtures";
import type { CartVm } from "@/lib/mappers/cart";
import { CART_CHECKOUT_BUTTON } from "../helpers/testIds";
import { createRouterMock } from "../helpers/nextNavigation";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/cart",
}));

const mockClearCart = vi.fn().mockResolvedValue(undefined);
const mockDeleteCartItem = vi.fn().mockResolvedValue({});
const mockUpdateCartItemQuantity = vi.fn().mockResolvedValue({});
const mockGetCart = vi.fn().mockResolvedValue({
  id: "cart-1",
  items: [],
  subtotal: "0.00",
  total: "0.00",
});

vi.mock("@/lib/api/cart", () => ({
  clearCart: (...args: unknown[]) => mockClearCart(...args),
  deleteCartItem: (...args: unknown[]) => mockDeleteCartItem(...args),
  getCart: (...args: unknown[]) => mockGetCart(...args),
  updateCartItemQuantity: (...args: unknown[]) => mockUpdateCartItemQuantity(...args),
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

// ── useAuth mock — controlled per test ───────────────────────────────────────

const mockUseAuth = vi.fn(
  (): { isAuthenticated: boolean; email: string | undefined } => ({
    isAuthenticated: false,
    email: undefined,
  }),
);

vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/components/cart/CartProvider", () => ({
  useCart: () => ({ refreshCart: vi.fn(), count: 0, resetCount: vi.fn() }),
  CartProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderClient(initialCartVm: CartVm = makeCart() as CartVm) {
  renderWithProviders(<CartDetailClient initialCartVm={initialCartVm} />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CartDetailClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Restore default resolved values after clearAllMocks
    mockClearCart.mockResolvedValue(undefined);
    mockUpdateCartItemQuantity.mockResolvedValue({});
    mockGetCart.mockResolvedValue({
      id: "cart-1",
      items: [],
      subtotal: "0.00",
      total: "0.00",
    });
  });

  describe("checkout routing based on auth state", () => {
    it("navigates to /checkout when authenticated user clicks checkout", async () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        email: "user@example.com",
      });
      const user = userEvent.setup();
      renderClient();
      await user.click(screen.getByTestId(CART_CHECKOUT_BUTTON));
      expect(mockRouter.push).toHaveBeenCalledWith("/checkout");
    });

    it("navigates to /guest/checkout when unauthenticated user clicks checkout", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false, email: undefined });
      const user = userEvent.setup();
      renderClient();
      await user.click(screen.getByTestId(CART_CHECKOUT_BUTTON));
      expect(mockRouter.push).toHaveBeenCalledWith("/guest/checkout");
    });
  });

  describe("continue shopping routing", () => {
    it("navigates to /products when continue shopping is clicked", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false, email: undefined });
      const user = userEvent.setup();
      renderClient();
      await user.click(
        screen.getByRole("button", { name: /continue shopping/i }),
      );
      expect(mockRouter.push).toHaveBeenCalledWith("/products");
    });
  });

  describe("onClearCart", () => {
    it("calls clearCart() once when confirmed", async () => {
      const user = userEvent.setup();
      // Render with a cart that has items so the clear button is visible
      renderClient(makeCart() as CartVm);

      // First click shows the confirmation UI
      await user.click(screen.getByRole("button", { name: /clear cart/i }));
      // Second click (Confirm) triggers onClearCart
      await user.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(mockClearCart).toHaveBeenCalledTimes(1);
      });
    });

    it("does not call deleteCartItem when clearing the cart", async () => {
      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(screen.getByRole("button", { name: /clear cart/i }));
      await user.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(mockClearCart).toHaveBeenCalledTimes(1);
      });

      expect(mockDeleteCartItem).not.toHaveBeenCalled();
    });

    it("calls getCart (refresh) after clearCart resolves", async () => {
      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(screen.getByRole("button", { name: /clear cart/i }));
      await user.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(mockGetCart).toHaveBeenCalled();
      });
    });
  });

  // ── Quantity increase / decrease (PATCH-backed) ─────────────────────────────

  describe("quantity increase / decrease via updateCartItemQuantity", () => {
    it("calls updateCartItemQuantity with incremented quantity on increase click", async () => {
      const user = userEvent.setup();
      // quantity 2 so decrease is also enabled; stockQuantity 10 allows increase
      const cartWithItem = makeCart({
        items: [makeCartItem({ quantity: 2 })],
      }) as CartVm;
      renderClient(cartWithItem);

      await user.click(
        screen.getByRole("button", { name: /increase quantity of test mouse/i }),
      );

      await waitFor(() => {
        expect(mockUpdateCartItemQuantity).toHaveBeenCalledWith({
          productId: 1,
          quantity: 3,
        });
      });
    });

    it("calls updateCartItemQuantity with decremented quantity on decrease click", async () => {
      const user = userEvent.setup();
      const cartWithItem = makeCart({
        items: [makeCartItem({ quantity: 2 })],
      }) as CartVm;
      renderClient(cartWithItem);

      await user.click(
        screen.getByRole("button", { name: /decrease quantity of test mouse/i }),
      );

      await waitFor(() => {
        expect(mockUpdateCartItemQuantity).toHaveBeenCalledWith({
          productId: 1,
          quantity: 1,
        });
      });
    });

    it("calls getCart (refresh) after quantity update resolves", async () => {
      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(
        screen.getByRole("button", { name: /increase quantity of test mouse/i }),
      );

      await waitFor(() => {
        expect(mockGetCart).toHaveBeenCalled();
      });
    });
  });
});
