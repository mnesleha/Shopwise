/**
 * CheckoutPriceChangeBanner — unit tests
 *
 * Spec coverage:
 * - persistent WARNING banner for major upward change
 * - persistent positive banner for major downward change
 * - item breakdown is rendered
 * - savings callout shown only for all-DOWN carts
 * - "View Order" triggers onContinue (only rendered when onContinue is provided)
 * - "Back to Cart" triggers onBackToCart
 * - "View Order" hidden when onContinue is omitted (preflight / step-1 context)
 * - mixed direction uses neutral wording
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckoutPriceChangeBanner } from "@/components/checkout/CheckoutPriceChangeBanner";
import { renderWithProviders } from "../helpers/render";
import {
  CHECKOUT_PRICE_CHANGE_BANNER,
  CHECKOUT_PRICE_CHANGE_CONTINUE,
  CHECKOUT_PRICE_CHANGE_BACK,
} from "../helpers/testIds";
import type { PriceChangeItem, PriceChangePayload } from "@/lib/api/checkout";

// ---------------------------------------------------------------------------
// Fixture factories
// ---------------------------------------------------------------------------

function makeItem(
  direction: "UP" | "DOWN",
  overrides: Partial<PriceChangeItem> = {},
): PriceChangeItem {
  return {
    product_id: 42,
    product_name: "Blue Sneakers",
    old_unit_gross: "50.00",
    new_unit_gross: direction === "UP" ? "55.00" : "45.00",
    absolute_change: "5.00",
    percent_change: "10.00",
    direction,
    severity: "WARNING",
    ...overrides,
  };
}

function makePayload(
  overrides: Partial<PriceChangePayload> = {},
): PriceChangePayload {
  return {
    has_changes: true,
    severity: "WARNING",
    affected_items: 1,
    items: [makeItem("UP")],
    ...overrides,
  };
}

function renderBanner(
  payload: PriceChangePayload,
  {
    onContinue = vi.fn(),
    onBackToCart = vi.fn(),
  }: { onContinue?: () => void; onBackToCart?: () => void } = {},
) {
  renderWithProviders(
    <CheckoutPriceChangeBanner
      payload={payload}
      onContinue={onContinue}
      onBackToCart={onBackToCart}
      currency="EUR"
    />,
  );
  return { onContinue, onBackToCart };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CheckoutPriceChangeBanner", () => {
  describe("warning banner — upward price change", () => {
    it("renders the banner container", () => {
      renderBanner(makePayload());
      expect(
        screen.getByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).toBeInTheDocument();
    });

    it("shows a price-change warning heading", () => {
      renderBanner(makePayload());
      expect(
        screen.getByText(/prices in your cart have changed/i),
      ).toBeInTheDocument();
    });

    it("does not show 'Good news' for upward changes", () => {
      renderBanner(makePayload());
      expect(screen.queryByText(/good news/i)).not.toBeInTheDocument();
    });
  });

  describe("positive banner — downward price change", () => {
    it("shows 'Good news' heading for all-DOWN carts", () => {
      renderBanner(makePayload({ items: [makeItem("DOWN")] }));
      expect(screen.getByText(/good news/i)).toBeInTheDocument();
    });

    it("shows savings callout for all-DOWN carts", () => {
      renderBanner(makePayload({ items: [makeItem("DOWN")] }));
      // "Your total decreased by EUR 5.00."
      const callout = screen.getByText(/your total decreased by/i);
      expect(callout).toBeInTheDocument();
      expect(callout.textContent).toMatch(/5\.00/);
    });

    it("does not show savings callout for upward changes", () => {
      renderBanner(makePayload({ items: [makeItem("UP")] }));
      expect(
        screen.queryByText(/your total decreased by/i),
      ).not.toBeInTheDocument();
    });
  });

  describe("mixed direction — neutral wording", () => {
    it("shows neutral heading for mixed-direction carts", () => {
      const mixedPayload = makePayload({
        items: [
          makeItem("UP", { product_id: 1, product_name: "Widget A" }),
          makeItem("DOWN", { product_id: 2, product_name: "Widget B" }),
        ],
        affected_items: 2,
      });
      renderBanner(mixedPayload);
      // Neutral heading — not "Good news"
      expect(screen.queryByText(/good news/i)).not.toBeInTheDocument();
      expect(
        screen.getByText(/prices in your cart have changed/i),
      ).toBeInTheDocument();
    });

    it("does not show savings callout for mixed-direction carts", () => {
      const mixedPayload = makePayload({
        items: [
          makeItem("UP", { product_id: 1 }),
          makeItem("DOWN", { product_id: 2 }),
        ],
      });
      renderBanner(mixedPayload);
      expect(
        screen.queryByText(/your total decreased by/i),
      ).not.toBeInTheDocument();
    });
  });

  describe("item breakdown", () => {
    it("renders product name in the item breakdown", () => {
      renderBanner(makePayload({ items: [makeItem("UP")] }));
      expect(screen.getByText(/blue sneakers/i)).toBeInTheDocument();
    });

    it("renders old and new prices", () => {
      renderBanner(makePayload({ items: [makeItem("UP")] }));
      expect(screen.getByText(/50\.00/)).toBeInTheDocument();
      expect(screen.getByText(/55\.00/)).toBeInTheDocument();
    });

    it("renders item testid for each changed item", () => {
      renderBanner(makePayload({ items: [makeItem("UP")] }));
      expect(screen.getByTestId("price-change-item-42")).toBeInTheDocument();
    });
  });

  describe("action buttons", () => {
    it("renders 'View Order' and 'Back to Cart' buttons when onContinue is provided", () => {
      renderBanner(makePayload());
      expect(
        screen.getByTestId(CHECKOUT_PRICE_CHANGE_CONTINUE),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId(CHECKOUT_PRICE_CHANGE_BACK),
      ).toBeInTheDocument();
    });

    it("hides 'View Order' button when onContinue is not provided", () => {
      // Preflight/step-1 usage — no onContinue supplied
      renderWithProviders(
        <CheckoutPriceChangeBanner
          payload={makePayload()}
          onBackToCart={vi.fn()}
        />,
      );
      expect(
        screen.queryByTestId(CHECKOUT_PRICE_CHANGE_CONTINUE),
      ).not.toBeInTheDocument();
      expect(
        screen.getByTestId(CHECKOUT_PRICE_CHANGE_BACK),
      ).toBeInTheDocument();
    });

    it("calls onContinue when 'View Order' is clicked", async () => {
      const user = userEvent.setup();
      const { onContinue } = renderBanner(makePayload());
      await user.click(screen.getByTestId(CHECKOUT_PRICE_CHANGE_CONTINUE));
      expect(onContinue).toHaveBeenCalledTimes(1);
    });

    it("calls onBackToCart when 'Back to Cart' is clicked", async () => {
      const user = userEvent.setup();
      const { onBackToCart } = renderBanner(makePayload());
      await user.click(screen.getByTestId(CHECKOUT_PRICE_CHANGE_BACK));
      expect(onBackToCart).toHaveBeenCalledTimes(1);
    });
  });
});
