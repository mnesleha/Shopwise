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
import { makeCart, makeCartItem, type CartThresholdRewardFixture } from "../helpers/fixtures";
import { CART_CHECKOUT_BUTTON, CART_THRESHOLD_REWARD, cartItem } from "../helpers/testIds";

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
    <CartDetail cart={makeCart()} {...callbacks} {...overrides} />,
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
      const cart = makeCart({
        items: [makeCartItem(), makeCartItem({ productId: "2" })],
      });
      renderCartDetail({ cart });
      expect(
        screen.getByRole("heading", { name: /your cart \(2 items\)/i }),
      ).toBeInTheDocument();
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
      await user.click(
        screen.getByRole("button", { name: /continue shopping/i }),
      );
      expect(onContinueShopping).toHaveBeenCalledTimes(1);
    });

    it("calls onRemoveItem with the productId when the remove button is clicked", async () => {
      const user = userEvent.setup();
      const cart = makeCart({
        items: [makeCartItem({ productId: "42", productName: "Widget" })],
      });
      const { onRemoveItem } = renderCartDetail({ cart });
      await user.click(
        screen.getByRole("button", { name: /remove widget from cart/i }),
      );
      expect(onRemoveItem).toHaveBeenCalledWith("42");
    });

    it("calls onDecreaseQty with the productId when minus button is clicked", async () => {
      const user = userEvent.setup();
      const cart = makeCart({
        items: [
          makeCartItem({ productId: "7", productName: "Gadget", quantity: 3 }),
        ],
      });
      const { onDecreaseQty } = renderCartDetail({ cart });
      await user.click(
        screen.getByRole("button", { name: /decrease quantity of gadget/i }),
      );
      expect(onDecreaseQty).toHaveBeenCalledWith("7");
    });

    it("calls onIncreaseQty with the productId when plus button is clicked", async () => {
      const user = userEvent.setup();
      const cart = makeCart({
        items: [
          makeCartItem({
            productId: "7",
            productName: "Gadget",
            quantity: 2,
            stockQuantity: 5,
          }),
        ],
      });
      const { onIncreaseQty } = renderCartDetail({ cart });
      await user.click(
        screen.getByRole("button", { name: /increase quantity of gadget/i }),
      );
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
        items: [
          makeCartItem({
            productName: "Gadget",
            quantity: 5,
            stockQuantity: 5,
          }),
        ],
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
      expect(
        screen.getByRole("button", { name: /confirm/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
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

  describe("discount display", () => {
    it("shows the original unit price struck-through when a discount applies", () => {
      const cart = makeCart({
        items: [
          makeCartItem({
            productId: "10",
            unitPrice: "44.99",
            originalUnitPrice: "49.99",
            discountLabel: "–10%",
          }),
        ],
      });
      renderCartDetail({ cart });

      const orig = screen.getByTestId("original-price");
      expect(orig).toBeInTheDocument();
      expect(orig).toHaveTextContent("49.99");
      expect(orig.className).toContain("line-through");
    });

    it("shows the discounted unit price prominently", () => {
      const cart = makeCart({
        items: [
          makeCartItem({
            productId: "10",
            unitPrice: "44.99",
            originalUnitPrice: "49.99",
            discountLabel: "–10%",
          }),
        ],
      });
      renderCartDetail({ cart });

      expect(screen.getByTestId("discounted-price")).toHaveTextContent("44.99");
    });

    it("shows the discount badge", () => {
      const cart = makeCart({
        items: [
          makeCartItem({
            productId: "10",
            unitPrice: "44.99",
            originalUnitPrice: "49.99",
            discountLabel: "–10%",
          }),
        ],
      });
      renderCartDetail({ cart });

      expect(screen.getByTestId("discount-badge")).toHaveTextContent("–10%");
    });

    it("shows no original-price or badge when no discount applies", () => {
      const cart = makeCart({
        items: [makeCartItem({ unitPrice: "29.99" })],
      });
      renderCartDetail({ cart });

      expect(screen.queryByTestId("original-price")).not.toBeInTheDocument();
      expect(screen.queryByTestId("discount-badge")).not.toBeInTheDocument();
    });
  });

  describe("order-level discount display (Phase 4 / Slice 3)", () => {
    it("renders the order discount row when orderDiscount is present", () => {
      const cart = makeCart({
        orderDiscount: {
          promotionName: "Spring Discount",
          amount: "10.00",
          totalGrossAfter: "90.00",
          totalTaxAfter: "16.83",
        },
      });
      renderCartDetail({ cart });
      expect(screen.getByTestId("order-discount-row")).toBeInTheDocument();
    });

    it("renders the order discount amount in the order discount row", () => {
      const cart = makeCart({
        orderDiscount: {
          promotionName: "Spring Discount",
          amount: "10.00",
          totalGrossAfter: "90.00",
          totalTaxAfter: "16.83",
        },
      });
      renderCartDetail({ cart });
      expect(screen.getByTestId("order-discount-amount")).toHaveTextContent(
        "10.00",
      );
    });

    it("renders 'Order discount' label in the discount row", () => {
      const cart = makeCart({
        orderDiscount: {
          promotionName: "Summer Sale",
          amount: "5.00",
          totalGrossAfter: "75.00",
          totalTaxAfter: "14.02",
        },
      });
      renderCartDetail({ cart });
      expect(screen.getByText(/order discount/i)).toBeInTheDocument();
    });

    it("does not render the order discount row when orderDiscount is absent", () => {
      const cart = makeCart({ orderDiscount: undefined });
      renderCartDetail({ cart });
      expect(screen.queryByTestId("order-discount-row")).not.toBeInTheDocument();
    });
  });

  describe("threshold reward banner (Phase 4 / Slice 4)", () => {
    function makeThresholdReward(
      overrides?: Partial<CartThresholdRewardFixture>,
    ): CartThresholdRewardFixture {
      return {
        isUnlocked: false,
        promotionName: "Free Shipping",
        remaining: "40.00",
        threshold: "100.00",
        ...overrides,
      };
    }

    it("renders the banner with data-state=pending when isUnlocked is false", () => {
      const cart = makeCart({ thresholdReward: makeThresholdReward() });
      renderCartDetail({ cart });
      const banner = screen.getByTestId(CART_THRESHOLD_REWARD);
      expect(banner).toBeInTheDocument();
      expect(banner).toHaveAttribute("data-state", "pending");
    });

    it("shows the remaining amount in the pending state", () => {
      const cart = makeCart({
        currency: "EUR",
        thresholdReward: makeThresholdReward({ remaining: "25.50" }),
      });
      renderCartDetail({ cart });
      expect(screen.getByTestId(CART_THRESHOLD_REWARD)).toHaveTextContent(
        "25.50",
      );
    });

    it("shows the promotion name in the pending state", () => {
      const cart = makeCart({
        thresholdReward: makeThresholdReward({ promotionName: "Gold Tier" }),
      });
      renderCartDetail({ cart });
      expect(screen.getByTestId(CART_THRESHOLD_REWARD)).toHaveTextContent(
        "Gold Tier",
      );
    });

    it("renders the banner with data-state=unlocked when isUnlocked is true", () => {
      const cart = makeCart({
        thresholdReward: makeThresholdReward({ isUnlocked: true, remaining: "0.00" }),
      });
      renderCartDetail({ cart });
      const banner = screen.getByTestId(CART_THRESHOLD_REWARD);
      expect(banner).toHaveAttribute("data-state", "unlocked");
    });

    it("shows '[name] has been applied.' text in the unlocked state", () => {
      const cart = makeCart({
        thresholdReward: makeThresholdReward({
          isUnlocked: true,
          remaining: "0.00",
          promotionName: "Free Shipping",
        }),
      });
      renderCartDetail({ cart });
      expect(screen.getByTestId(CART_THRESHOLD_REWARD)).toHaveTextContent(
        "Free Shipping has been applied.",
      );
    });

    it("does not render the banner when thresholdReward is absent", () => {
      const cart = makeCart({ thresholdReward: undefined });
      renderCartDetail({ cart });
      expect(
        screen.queryByTestId(CART_THRESHOLD_REWARD),
      ).not.toBeInTheDocument();
    });
  });
});
