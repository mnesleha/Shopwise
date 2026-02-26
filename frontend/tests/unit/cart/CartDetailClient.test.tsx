/**
 * CartDetailClient — Type B (Client adapter)
 *
 * Contract guarded:
 * - "Proceed to checkout" navigates to /checkout when user is authenticated
 * - "Proceed to checkout" navigates to /guest/checkout when user is not authenticated
 * - "Continue shopping" navigates to /products
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import * as React from "react";
import userEvent from "@testing-library/user-event";
import CartDetailClient from "@/components/cart/CartDetailClient";
import { renderWithProviders } from "../helpers/render";
import { makeCart } from "../helpers/fixtures";
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

vi.mock("@/lib/api/cart", () => ({
  deleteCartItem: vi.fn().mockResolvedValue({}),
  getCart: vi.fn().mockResolvedValue({ id: "cart-1", items: [], subtotal: "0.00", total: "0.00" }),
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

// ── useAuth mock — controlled per test ───────────────────────────────────────

const mockUseAuth = vi.fn((): { isAuthenticated: boolean; email: string | undefined } => ({
  isAuthenticated: false,
  email: undefined,
}));

vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderClient(initialCartVm: CartVm = makeCart() as CartVm) {
  renderWithProviders(<CartDetailClient initialCartVm={initialCartVm} />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CartDetailClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("checkout routing based on auth state", () => {
    it("navigates to /checkout when authenticated user clicks checkout", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true, email: "user@example.com" });
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
      await user.click(screen.getByRole("button", { name: /continue shopping/i }));
      expect(mockRouter.push).toHaveBeenCalledWith("/products");
    });
  });
});
