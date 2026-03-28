/**
 * CheckoutForm — preflight / priceChangePayload behaviour
 *
 * Spec coverage:
 * - No priceChangePayload  → price-change banner NOT shown in step 1
 * - WARNING payload        → price-change banner IS shown in step 1
 * - NONE / INFO payload    → price-change banner NOT shown in step 1
 * - Banner NOT in step 2   → advance via Continue, banner disappears
 * - Banner NOT on back      → once acknowledged, never reappears on back-navigation
 * - "Back to Cart" inside banner calls onBackToCart
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { renderWithProviders } from "../helpers/render";
import {
  CHECKOUT_CONTINUE,
  CHECKOUT_BACK,
  CHECKOUT_PRICE_CHANGE_BANNER,
} from "../helpers/testIds";
import type { PriceChangePayload } from "@/lib/api/checkout";

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

function makeWarningPayload(
  overrides: Partial<PriceChangePayload> = {},
): PriceChangePayload {
  return {
    has_changes: true,
    severity: "WARNING",
    affected_items: 1,
    items: [
      {
        product_id: 10,
        product_name: "Fancy Watch",
        old_unit_gross: "100.00",
        new_unit_gross: "120.00",
        absolute_change: "20.00",
        percent_change: "20.00",
        direction: "UP",
        severity: "WARNING",
      },
    ],
    ...overrides,
  };
}

function makeInfoPayload(): PriceChangePayload {
  return makeWarningPayload({ severity: "INFO" });
}

function makeNonePayload(): PriceChangePayload {
  return {
    has_changes: false,
    severity: "NONE",
    affected_items: 0,
    items: [],
  };
}

// ---------------------------------------------------------------------------
// Render helper
// ---------------------------------------------------------------------------

function renderForm(priceChangePayload?: PriceChangePayload | null) {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onBackToCart = vi.fn();
  renderWithProviders(
    <CheckoutForm
      onSubmit={onSubmit}
      onBackToCart={onBackToCart}
      priceChangePayload={priceChangePayload}
    />,
  );
  return { onSubmit, onBackToCart };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CheckoutForm — priceChangePayload / preflight banner", () => {
  describe("no payload provided", () => {
    it("does not render the price-change banner in step 1", () => {
      renderForm(); // no priceChangePayload
      expect(
        screen.queryByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).not.toBeInTheDocument();
    });
  });

  describe("WARNING payload", () => {
    it("renders the price-change banner in step 1", () => {
      renderForm(makeWarningPayload());
      expect(
        screen.getByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).toBeInTheDocument();
    });

    it("does NOT render the banner in step 2 after advancing", async () => {
      const user = userEvent.setup();
      renderForm(makeWarningPayload());
      // Advance to step 2
      await user.click(screen.getByTestId(CHECKOUT_CONTINUE));
      expect(
        screen.queryByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).not.toBeInTheDocument();
    });

    it("does NOT reappear after navigating back from step 2 to step 1", async () => {
      const user = userEvent.setup();
      renderForm(makeWarningPayload());
      // Advance to step 2 — this acknowledges the banner
      await user.click(screen.getByTestId(CHECKOUT_CONTINUE));
      // Go back to step 1
      await user.click(screen.getByTestId(CHECKOUT_BACK));
      // Banner must stay hidden — once acknowledged it should never come back
      expect(
        screen.queryByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).not.toBeInTheDocument();
    });

    it("'Back to Cart' inside banner calls onBackToCart", async () => {
      const user = userEvent.setup();
      const { onBackToCart } = renderForm(makeWarningPayload());
      await user.click(screen.getByTestId("checkout-price-change-back"));
      expect(onBackToCart).toHaveBeenCalledTimes(1);
    });

    it("does NOT render 'View Order' button (no onContinue in preflight context)", () => {
      renderForm(makeWarningPayload());
      expect(
        screen.queryByTestId("checkout-price-change-continue"),
      ).not.toBeInTheDocument();
    });
  });

  describe("INFO payload", () => {
    it("does NOT render the banner — INFO is handled as a toast at page level", () => {
      renderForm(makeInfoPayload());
      expect(
        screen.queryByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).not.toBeInTheDocument();
    });
  });

  describe("NONE payload", () => {
    it("does NOT render the banner when severity is NONE", () => {
      renderForm(makeNonePayload());
      expect(
        screen.queryByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).not.toBeInTheDocument();
    });
  });

  describe("null / undefined payload", () => {
    it("does not render banner for null payload", () => {
      renderForm(null);
      expect(
        screen.queryByTestId(CHECKOUT_PRICE_CHANGE_BANNER),
      ).not.toBeInTheDocument();
    });
  });
});
