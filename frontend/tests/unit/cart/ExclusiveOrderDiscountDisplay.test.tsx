/**
 * Exclusive order-level promotion display — storefront invariants.
 *
 * Contract guarded:
 * - Exactly one order-discount row is rendered when the backend signals an
 *   active order-level discount (no multi-winner or duplicate rows).
 * - The displayed discount amount comes directly from the backend payload.
 * - No non-winning offer messaging (conflict text, "better discount", etc.)
 *   is rendered.
 * - When the backend signals no order-level discount, the row is absent.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { CartDetail } from "@/components/cart/CartDetail";
import { renderWithProviders } from "../helpers/render";
import { makeCart, makeCartItem } from "../helpers/fixtures";

function renderWith(
  overrides?: Partial<React.ComponentProps<typeof CartDetail>>,
) {
  renderWithProviders(
    <CartDetail
      cart={makeCart()}
      onContinueShopping={vi.fn()}
      onRemoveItem={vi.fn()}
      onDecreaseQty={vi.fn()}
      onIncreaseQty={vi.fn()}
      onClearCart={vi.fn()}
      onCheckout={vi.fn()}
      {...overrides}
    />,
  );
}

const cartWithDiscount = makeCart({
  items: [makeCartItem({ productId: "1", unitPrice: "100.00", quantity: 1 })],
  subtotal: "100.00",
  total: "80.00",
  orderDiscount: {
    promotionName: "Spring Sale 20% Off",
    amount: "20.00",
    totalGrossAfter: "80.00",
    totalTaxAfter: "0.00",
  },
});

describe("CartDetail — exclusive order-level discount display", () => {
  it("renders exactly one order-discount row when the backend applies a discount", () => {
    renderWith({ cart: cartWithDiscount });

    const rows = screen.getAllByTestId("order-discount-row");
    expect(rows).toHaveLength(1);
  });

  it("shows the discount amount from the backend payload", () => {
    renderWith({ cart: cartWithDiscount });

    const amountEl = screen.getByTestId("order-discount-amount");
    expect(amountEl.textContent).toContain("20.00");
  });

  it("does not render the order-discount row when no order discount is active", () => {
    const cartNoDiscount = makeCart({
      items: [makeCartItem()],
      subtotal: "100.00",
      total: "100.00",
    });
    renderWith({ cart: cartNoDiscount });

    expect(screen.queryByTestId("order-discount-row")).not.toBeInTheDocument();
  });

  it("renders no secondary or duplicate discount rows", () => {
    renderWith({ cart: cartWithDiscount });

    const rows = screen.queryAllByTestId("order-discount-row");
    expect(rows.length).toBeLessThanOrEqual(1);
  });

  it("does not render any non-winning offer message or conflict text", () => {
    renderWith({ cart: cartWithDiscount });

    const bodyText = document.body.textContent ?? "";
    expect(bodyText).not.toMatch(/conflict/i);
    expect(bodyText).not.toMatch(/competing/i);
    expect(bodyText).not.toMatch(/better discount/i);
    expect(bodyText).not.toMatch(/another offer/i);
  });

  it("SUPERSEDED message is customer-neutral — no priority or internal mechanics exposed", () => {
    // When a campaign offer is superseded, the storefront should show a simple
    // neutral message.  It must not reveal priority levels, promotion IDs, or
    // any internal resolution detail that could confuse the customer.
    const cartSuperseded = makeCart({
      items: [
        makeCartItem({ productId: "1", unitPrice: "100.00", quantity: 1 }),
      ],
      subtotal: "100.00",
      total: "50.00",
      orderDiscount: {
        promotionName: "Auto Apply Winner",
        amount: "50.00",
        totalGrossAfter: "50.00",
        totalTaxAfter: "0.00",
      },
      campaignOutcome: "SUPERSEDED",
    });
    renderWith({ cart: cartSuperseded });

    const banner = document.querySelector(
      "[data-testid='campaign-outcome-superseded']",
    );
    expect(banner).not.toBeNull();
    const text = banner!.textContent ?? "";
    // Correct customer-safe wording:
    expect(text).toContain("A better discount is already applied");
    // Must NOT expose internal mechanics:
    expect(text).not.toMatch(/priority/i);
    expect(text).not.toMatch(/superseded/i);
    expect(text).not.toMatch(/auto.?apply/i);
    expect(text).not.toMatch(/campaign.*lost/i);
  });

  it("does not render an upgrade banner unless the backend explicitly signals one", () => {
    // Guards against a regression where the frontend would predict or invent
    // upgrade messaging without a backend signal — all upgrade logic must live
    // in the backend decision engine.
    renderWith({ cart: cartWithDiscount });

    expect(
      document.querySelector("[data-testid='order-discount-upgrade-banner']"),
    ).toBeNull();
  });
});
