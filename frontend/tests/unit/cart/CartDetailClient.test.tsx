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
 * - Shows toast.error "Not enough stock available." on 409 from updateCartItemQuantity
 * - Shows generic toast.error on non-409 errors from updateCartItemQuantity
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import * as React from "react";
import { act } from "react";
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

const mockAddCartItem = vi.fn().mockResolvedValue(undefined);
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
  addCartItem: (...args: unknown[]) => mockAddCartItem(...args),
  clearCart: (...args: unknown[]) => mockClearCart(...args),
  deleteCartItem: (...args: unknown[]) => mockDeleteCartItem(...args),
  getCart: (...args: unknown[]) => mockGetCart(...args),
  updateCartItemQuantity: (...args: unknown[]) =>
    mockUpdateCartItemQuantity(...args),
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
  useCart: () => ({
    refreshCart: vi.fn(),
    count: 0,
    resetCount: vi.fn(),
    orderDiscountApplied: false,
    orderDiscountAmount: null,
    orderDiscountPromotionName: null,
  }),
  CartProvider: ({ children }: { children: React.ReactNode }) => children,
}));

const mockToastError = vi.fn();
const mockToastSuccess = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: (...args: unknown[]) => mockToastSuccess(...args),
    dismiss: vi.fn(),
  },
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
    mockAddCartItem.mockResolvedValue(undefined);
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
    it("calls clearCart() once when clear cart is clicked", async () => {
      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(screen.getByRole("button", { name: /clear cart/i }));

      await waitFor(() => {
        expect(mockClearCart).toHaveBeenCalledTimes(1);
      });
    });

    it("does not call deleteCartItem when clearing the cart", async () => {
      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(screen.getByRole("button", { name: /clear cart/i }));

      await waitFor(() => {
        expect(mockClearCart).toHaveBeenCalledTimes(1);
      });

      expect(mockDeleteCartItem).not.toHaveBeenCalled();
    });

    it("calls getCart (refresh) after clearCart resolves", async () => {
      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(screen.getByRole("button", { name: /clear cart/i }));

      await waitFor(() => {
        expect(mockGetCart).toHaveBeenCalled();
      });
    });

    it("shows an undo toast with an extended duration after clearing the cart", async () => {
      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(screen.getByRole("button", { name: /clear cart/i }));

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith(
          "Cart cleared.",
          expect.objectContaining({
            duration: 12000,
            action: expect.objectContaining({ label: "Undo" }),
          }),
        );
      });
    });

    it("restores cleared items when undo is clicked", async () => {
      const user = userEvent.setup();
      renderClient(
        makeCart({
          items: [
            makeCartItem({
              productId: "7",
              productName: "Travel Mug",
              quantity: 2,
            }),
          ],
        }) as CartVm,
      );

      await user.click(screen.getByRole("button", { name: /clear cart/i }));

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalled();
      });

      const toastOptions = mockToastSuccess.mock.calls.find(
        ([message]) => message === "Cart cleared.",
      )?.[1] as { action?: { onClick?: () => void } } | undefined;

      expect(toastOptions?.action?.onClick).toBeTypeOf("function");

      await act(async () => {
        toastOptions?.action?.onClick?.();
      });

      await waitFor(() => {
        expect(mockAddCartItem).toHaveBeenCalledWith({
          productId: 7,
          quantity: 2,
        });
      });

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith("Cart restored.");
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
        screen.getByRole("button", {
          name: /increase quantity of test mouse/i,
        }),
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
        screen.getByRole("button", {
          name: /decrease quantity of test mouse/i,
        }),
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
        screen.getByRole("button", {
          name: /increase quantity of test mouse/i,
        }),
      );

      await waitFor(() => {
        expect(mockGetCart).toHaveBeenCalled();
      });
    });
  });

  // ── Stock-conflict error handling (409) ───────────────────────────────────────

  describe("409 stock-conflict error handling", () => {
    it('shows "Not enough stock available." toast on 409 from updateCartItemQuantity', async () => {
      const stockError = Object.assign(new Error("Conflict"), {
        response: { status: 409 },
      });
      mockUpdateCartItemQuantity.mockRejectedValueOnce(stockError);

      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(
        screen.getByRole("button", {
          name: /increase quantity of test mouse/i,
        }),
      );

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          "Not enough stock available.",
        );
      });
    });

    it("shows generic error toast on non-409 errors from updateCartItemQuantity", async () => {
      const serverError = Object.assign(new Error("Server Error"), {
        response: { status: 500 },
      });
      mockUpdateCartItemQuantity.mockRejectedValueOnce(serverError);

      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(
        screen.getByRole("button", {
          name: /increase quantity of test mouse/i,
        }),
      );

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          "Could not update quantity. Please try again.",
        );
      });
    });

    it("still calls getCart (refresh) after a 409 error to re-sync cart state", async () => {
      const stockError = Object.assign(new Error("Conflict"), {
        response: { status: 409 },
      });
      mockUpdateCartItemQuantity.mockRejectedValueOnce(stockError);

      const user = userEvent.setup();
      renderClient(makeCart() as CartVm);

      await user.click(
        screen.getByRole("button", {
          name: /increase quantity of test mouse/i,
        }),
      );

      await waitFor(() => {
        expect(mockGetCart).toHaveBeenCalled();
      });
    });
  });
});
