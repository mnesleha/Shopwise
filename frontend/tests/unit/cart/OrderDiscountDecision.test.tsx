/**
 * Order discount decision engine — storefront messaging tests.
 *
 * Phase 4 / Slice 5C
 *
 * Contract guarded:
 *
 * CartDetail rendering:
 * - Upgrade banner (order-discount-upgrade-banner) is shown with correct text
 *   when cart.orderDiscountUpgrade is present.
 * - Upgrade banner is absent when cart.orderDiscountUpgrade is undefined.
 * - SUPERSEDED banner (campaign-outcome-superseded) is shown when
 *   cart.campaignOutcome === "SUPERSEDED".
 * - SUPERSEDED banner is absent when campaignOutcome is "APPLIED" or undefined.
 * - Neither banner is shown on a plain cart with no decision state.
 *
 * Cart mapper (mapCartToVm):
 * - campaign_outcome "APPLIED" is mapped to campaignOutcome.
 * - campaign_outcome "SUPERSEDED" is mapped to campaignOutcome.
 * - campaign_outcome null/absent leaves campaignOutcome undefined.
 * - order_discount_next_upgrade is mapped to orderDiscountUpgrade.
 * - absent order_discount_next_upgrade leaves orderDiscountUpgrade undefined.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import * as React from "react";
import { CartDetail } from "@/components/cart/CartDetail";
import { mapCartToVm } from "@/lib/mappers/cart";
import { renderWithProviders } from "../helpers/render";
import { makeCart, makeCartItem } from "../helpers/fixtures";
import type { CartTotalsDto } from "@/lib/api/cart";

// ---------------------------------------------------------------------------
// CartDetail rendering helpers
// ---------------------------------------------------------------------------

function renderCartDetail(
  overrides?: Partial<React.ComponentProps<typeof CartDetail>>,
) {
  renderWithProviders(
    <CartDetail
      cart={makeCart({
        items: [
          makeCartItem({ productId: "1", unitPrice: "100.00", quantity: 1 }),
        ],
        subtotal: "100.00",
        total: "80.00",
        orderDiscount: {
          promotionName: "Existing 20% Off",
          amount: "20.00",
          totalGrossAfter: "80.00",
          totalTaxAfter: "0.00",
        },
      })}
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

// ---------------------------------------------------------------------------
// Upgrade banner tests
// ---------------------------------------------------------------------------

describe("CartDetail — order-discount-upgrade-banner", () => {
  it("shows the upgrade banner when orderDiscountUpgrade is present", () => {
    renderCartDetail({
      cart: makeCart({
        items: [
          makeCartItem({ productId: "1", unitPrice: "100.00", quantity: 1 }),
        ],
        subtotal: "100.00",
        total: "80.00",
        orderDiscount: {
          promotionName: "Existing Discount",
          amount: "20.00",
          totalGrossAfter: "80.00",
          totalTaxAfter: "0.00",
        },
        orderDiscountUpgrade: {
          threshold: "500.00",
          remaining: "150.00",
          promotionName: "€60 Off",
          currency: "EUR",
        },
      }),
    });

    expect(
      screen.getByTestId("order-discount-upgrade-banner"),
    ).toBeInTheDocument();
  });

  it("includes the promotion name in the upgrade banner text", () => {
    renderCartDetail({
      cart: makeCart({
        items: [
          makeCartItem({ productId: "1", unitPrice: "350.00", quantity: 1 }),
        ],
        subtotal: "350.00",
        total: "315.00",
        orderDiscount: {
          promotionName: "Auto 10%",
          amount: "35.00",
          totalGrossAfter: "315.00",
          totalTaxAfter: "0.00",
        },
        orderDiscountUpgrade: {
          threshold: "500.00",
          remaining: "150.00",
          promotionName: "Summer Fixed 60",
          currency: "EUR",
        },
      }),
    });

    const banner = screen.getByTestId("order-discount-upgrade-banner");
    expect(banner.textContent).toContain("Summer Fixed 60");
    expect(banner.textContent).toContain("150.00");
  });

  it("does not show the upgrade banner when orderDiscountUpgrade is absent", () => {
    renderCartDetail({
      cart: makeCart({
        items: [
          makeCartItem({ productId: "1", unitPrice: "100.00", quantity: 1 }),
        ],
        subtotal: "100.00",
        total: "80.00",
        orderDiscount: {
          promotionName: "Existing Discount",
          amount: "20.00",
          totalGrossAfter: "80.00",
          totalTaxAfter: "0.00",
        },
      }),
    });

    expect(
      screen.queryByTestId("order-discount-upgrade-banner"),
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SUPERSEDED banner tests
// ---------------------------------------------------------------------------

describe("CartDetail — campaign-outcome-superseded", () => {
  it("shows the SUPERSEDED banner when campaignOutcome is 'SUPERSEDED'", () => {
    renderCartDetail({
      cart: makeCart({
        items: [
          makeCartItem({ productId: "1", unitPrice: "100.00", quantity: 1 }),
        ],
        subtotal: "100.00",
        total: "50.00",
        orderDiscount: {
          promotionName: "Big Auto Apply",
          amount: "50.00",
          totalGrossAfter: "50.00",
          totalTaxAfter: "0.00",
        },
        campaignOutcome: "SUPERSEDED",
      }),
    });

    const banner = screen.getByTestId("campaign-outcome-superseded");
    expect(banner).toBeInTheDocument();
    expect(banner.textContent).toContain(
      "A better discount is already applied",
    );
  });

  it("does not show the SUPERSEDED banner when campaignOutcome is 'APPLIED'", () => {
    renderCartDetail({
      cart: makeCart({
        items: [
          makeCartItem({ productId: "1", unitPrice: "100.00", quantity: 1 }),
        ],
        subtotal: "100.00",
        total: "60.00",
        orderDiscount: {
          promotionName: "My Campaign Offer",
          amount: "40.00",
          totalGrossAfter: "60.00",
          totalTaxAfter: "0.00",
        },
        campaignOutcome: "APPLIED",
      }),
    });

    expect(
      screen.queryByTestId("campaign-outcome-superseded"),
    ).not.toBeInTheDocument();
  });

  it("does not show the SUPERSEDED banner when campaignOutcome is absent", () => {
    renderCartDetail();

    expect(
      screen.queryByTestId("campaign-outcome-superseded"),
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Mapper tests
// ---------------------------------------------------------------------------

/** Minimal totals DTO with required fields, new fields absent by default. */
function makeTotalsDto(overrides: Partial<CartTotalsDto> = {}): CartTotalsDto {
  return {
    subtotal_undiscounted: "100.00",
    subtotal_discounted: "100.00",
    total_discount: "0.00",
    total_tax: "0.00",
    total_gross: "100.00",
    currency: "EUR",
    item_count: 1,
    order_discount_applied: false,
    order_discount_amount: null,
    order_discount_promotion_code: null,
    order_discount_promotion_name: null,
    total_gross_after_order_discount: null,
    total_tax_after_order_discount: null,
    ...overrides,
  };
}

function makeCartDto(totalsOverrides: Partial<CartTotalsDto> = {}) {
  return {
    id: 1,
    status: "ACTIVE",
    items: [],
    totals: makeTotalsDto(totalsOverrides),
  };
}

describe("mapCartToVm — campaign outcome (Phase 4 / Slice 5C)", () => {
  it("maps campaign_outcome 'APPLIED' to campaignOutcome", () => {
    const vm = mapCartToVm(makeCartDto({ campaign_outcome: "APPLIED" }));
    expect(vm.campaignOutcome).toBe("APPLIED");
  });

  it("maps campaign_outcome 'SUPERSEDED' to campaignOutcome", () => {
    const vm = mapCartToVm(makeCartDto({ campaign_outcome: "SUPERSEDED" }));
    expect(vm.campaignOutcome).toBe("SUPERSEDED");
  });

  it("leaves campaignOutcome undefined when campaign_outcome is null", () => {
    const vm = mapCartToVm(makeCartDto({ campaign_outcome: null }));
    expect(vm.campaignOutcome).toBeUndefined();
  });

  it("leaves campaignOutcome undefined when campaign_outcome is absent", () => {
    const vm = mapCartToVm(makeCartDto());
    expect(vm.campaignOutcome).toBeUndefined();
  });
});

describe("mapCartToVm — order discount upgrade (Phase 4 / Slice 5C)", () => {
  it("maps order_discount_next_upgrade to orderDiscountUpgrade", () => {
    const vm = mapCartToVm(
      makeCartDto({
        order_discount_next_upgrade: {
          threshold: "500.00",
          remaining: "150.00",
          promotion_name: "Summer €60",
          currency: "EUR",
        },
      }),
    );

    expect(vm.orderDiscountUpgrade).toEqual({
      threshold: "500.00",
      remaining: "150.00",
      promotionName: "Summer €60",
      currency: "EUR",
    });
  });

  it("leaves orderDiscountUpgrade undefined when order_discount_next_upgrade is null", () => {
    const vm = mapCartToVm(makeCartDto({ order_discount_next_upgrade: null }));
    expect(vm.orderDiscountUpgrade).toBeUndefined();
  });

  it("leaves orderDiscountUpgrade undefined when order_discount_next_upgrade is absent", () => {
    const vm = mapCartToVm(makeCartDto());
    expect(vm.orderDiscountUpgrade).toBeUndefined();
  });
});
