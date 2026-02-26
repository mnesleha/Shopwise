/**
 * CartDetail — Type A (Presentational)
 *
 * Contract guarded:
 * - Renders each item's name, price, and quantity
 * - Each item has the correct data-testid
 * - Checkout button calls onCheckout
 * - "Continue shopping" calls onContinueShopping
 * - Remove button calls onRemoveItem with correct productId
 * - Decrease / Increase qty buttons call the correct callbacks
 * - Decrease qty is disabled when quantity is 1
 * - Increase qty is disabled when stock limit is reached
 * - Clear cart shows a confirmation prompt before calling onClearCart
 * - Empty cart state is rendered when items array is empty
 * - Subtotal and total are displayed
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CartDetail } from "@/components/cart/CartDetail";
import { renderWithProviders } from "../helpers/render";
import { makeCart, makeCartItem } from "../helpers/fixtures";
import { CART_CHECKOUT_BUTTON, cartItem } from "../helpers/testIds";

function renderCartDetail(
  overrides?: Partial<React.ComponentProps<typeof CartDetail>>,
) {
  const callbacks = {
    onContinueShopping: vi.fn(),
    onRemoveItem: vi.fn(),
    onDecreaseQty: vi.fn(),
    onIncreaseQty: vi.fn(),
    onClearCart: vi.fn(),
    onCheckout: vi.fn(),
  };

  renderWithProviders(
    <CartDetail
      cart={makeCart()}
      {...callbacks}
      {...overrides}
    />,
  );

  return callbacks;
}

describe("CartDetail", () => {
  describe("rendering items", () => {
    it("renders the product name of each cart item", () => {
      const cart = makeCart({
        items: [makeCartItem({ productName: "Wireless Mouse" })],
      });
      renderCartDetail({ cart });
      expect(screen.getByText("Wireless Mouse")).toBeInTheDocument();
    });

    it("renders the unit price of each cart item", () => {
      const cart = makeCart({
        items: [makeCartItem({ unitPrice: "49.90" })],
      });
      renderCartDetail({ cart });
      expect(screen.getByText("49.90", { exact: false })).toBeInTheDocument();
    });

    it("renders the correct data-testid for each cart item", () => {
      const cart = makeCart({
        items: [makeCartItem({ productId: "99" })],
      });
      renderCartDetail({ cart });
      expect(screen.getByTestId(cartItem("99"))).toBeInTheDocument();
    });

    it("renders the item count in the heading", () => {
      const cart = makeCart({ items: [makeCartItem(), makeCartItem({ productId: "2" })] });
      renderCartDetail({ cart });
      expect(screen.getByRole("heading", { name: /your cart \(2 items\)/i })).toBeInTheDocument();
    });

    it("shows subtotal and total in the order summary", () => {
      const cart = makeCart({ subtotal: "59.98", total: "59.98" });
      renderCartDetail({ cart });
      expect(screen.getAllByText(/59\.98/).length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("empty state", () => {
    it("renders the empty cart message when items array is empty", () => {
      const cart = makeCart({ items: [] });
      renderCartDetail({ cart });
      expect(screen.getByText(/your cart is empty/i)).toBeInTheDocument();
    });

    it("does NOT render the checkout button when cart is empty", () => {
      const cart = makeCart({ items: [] });
      renderCartDetail({ cart });
      expect(screen.queryByTestId(CART_CHECKOUT_BUTTON)).toBeNull();
    });
  });

  describe("callbacks", () => {
    it("calls onCheckout when the checkout button is clicked", async () => {
      const user = userEvent.setup();
      const { onCheckout } = renderCartDetail();
      await user.click(screen.getByTestId(CART_CHECKOUT_BUTTON));
      expect(onCheckout).toHaveBeenCalledTimes(1);
    });

    it("calls onContinueShopping when the continue shopping button is clicked", async () => {
      const user = userEvent.setup();
      const { onContinueShopping } = renderCartDetail();
      await user.click(screen.getByRole("button", { name: /continue shopping/i }));
      expect(onContinueShopping).toHaveBeenCalledTimes(1);
    });

    it("calls onRemoveItem with the productId when the remove button is clicked", async () => {
      const user = userEvent.setup();
      const cart = makeCart({ items: [makeCartItem({ productId: "42", productName: "Widget" })] });
      const { onRemoveItem } = renderCartDetail({ cart });
      await user.click(screen.getByRole("button", { name: /remove widget from cart/i }));
      expect(onRemoveItem).toHaveBeenCalledWith("42");
    });

    it("calls onDecreaseQty with the productId when minus button is clicked", async () => {
      const user = userEvent.setup();
      const cart = makeCart({
        items: [makeCartItem({ productId: "7", productName: "Gadget", quantity: 3 })],
      });
      const { onDecreaseQty } = renderCartDetail({ cart });
      await user.click(screen.getByRole("button", { name: /decrease quantity of gadget/i }));
      expect(onDecreaseQty).toHaveBeenCalledWith("7");
    });

    it("calls onIncreaseQty with the productId when plus button is clicked", async () => {
      const user = userEvent.setup();
      const cart = makeCart({
        items: [makeCartItem({ productId: "7", productName: "Gadget", quantity: 2, stockQuantity: 5 })],
      });
      const { onIncreaseQty } = renderCartDetail({ cart });
      await user.click(screen.getByRole("button", { name: /increase quantity of gadget/i }));
      expect(onIncreaseQty).toHaveBeenCalledWith("7");
    });
  });

  describe("quantity controls", () => {
    it("disables the decrease button when quantity is 1", () => {
      const cart = makeCart({
        items: [makeCartItem({ productName: "Gadget", quantity: 1 })],
      });
      renderCartDetail({ cart });
      expect(
        screen.getByRole("button", { name: /decrease quantity of gadget/i }),
      ).toBeDisabled();
    });

    it("disables the increase button when stock limit is reached", () => {
      const cart = makeCart({
        items: [makeCartItem({ productName: "Gadget", quantity: 5, stockQuantity: 5 })],
      });
      renderCartDetail({ cart });
      expect(
        screen.getByRole("button", { name: /increase quantity of gadget/i }),
      ).toBeDisabled();
    });
  });

  describe("clear cart confirmation flow", () => {
    it("shows a confirmation prompt after the first click on clear cart", async () => {
      const user = userEvent.setup();
      renderCartDetail();
      await user.click(screen.getByRole("button", { name: /clear cart/i }));
      expect(screen.getByText(/clear all\?/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    });

    it("calls onClearCart when the confirm button is clicked", async () => {
      const user = userEvent.setup();
      const { onClearCart } = renderCartDetail();
      await user.click(screen.getByRole("button", { name: /clear cart/i }));
      await user.click(screen.getByRole("button", { name: /confirm/i }));
      expect(onClearCart).toHaveBeenCalledTimes(1);
    });

    it("hides the confirmation prompt when cancel is clicked", async () => {
      const user = userEvent.setup();
      renderCartDetail();
      await user.click(screen.getByRole("button", { name: /clear cart/i }));
      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(screen.queryByText(/clear all\?/i)).toBeNull();
    });
  });
});
