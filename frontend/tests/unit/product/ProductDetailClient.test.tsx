/**
 * ProductDetailClient — Type B (Client adapter)
 *
 * Tests the routing and API contracts wired by ProductDetailClient.
 * Mocks next/navigation and the cart API. Renders ProductDetail under the hood.
 */

import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { makeProduct } from "../helpers/fixtures";
import { createRouterMock } from "../helpers/nextNavigation";

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

const mockAddCartItem = vi.fn();
vi.mock("@/lib/api/cart", () => ({
  addCartItem: (...args: unknown[]) => mockAddCartItem(...args),
}));

// Import after mocks are set up
import ProductDetailClient from "@/components/product/ProductDetailClient";

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  mockAddCartItem.mockResolvedValue(undefined);
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ProductDetailClient — routing contracts", () => {
  it("navigates to /products when the back button is clicked", async () => {
    const user = userEvent.setup();
    render(<ProductDetailClient product={makeProduct({ id: "10" })} />);

    const backButtons = screen.getAllByRole("button", { name: /back/i });
    await user.click(backButtons[0]);

    expect(mockRouter.push).toHaveBeenCalledOnce();
    expect(mockRouter.push).toHaveBeenCalledWith("/products");
  });

  it("calls addCartItem and navigates to /cart when add-to-cart is clicked", async () => {
    const user = userEvent.setup();
    render(<ProductDetailClient product={makeProduct({ id: "10", stockQuantity: 5 })} />);

    await user.click(screen.getByRole("button", { name: /add to cart/i }));

    expect(mockAddCartItem).toHaveBeenCalledOnce();
    expect(mockAddCartItem).toHaveBeenCalledWith({ productId: 10, quantity: 1 });
    // Router.push("/cart") is called after the async addCartItem resolves
    await vi.waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith("/cart");
    });
  });
});
