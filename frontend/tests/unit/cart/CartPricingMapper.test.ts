/**
 * CartPricingMapper — Phase 2 / Slice 4
 *
 * Tests for mapCartToVm with the new backend-computed pricing fields.
 *
 * Contract guarded:
 * - Backend totals are used when present
 * - Discount line appears when total_discount > 0
 * - Discount is hidden when total_discount is 0
 * - Item unitPrice uses discounted gross from per-item pricing
 * - Item unitPrice falls back to price_at_add_time when pricing absent
 * - Tax is populated from total_tax when > 0
 * - Empty cart maps safely with zero totals
 * - Legacy response without totals falls back to manual calculation
 */
import { describe, it, expect } from "vitest";
import { mapCartToVm } from "@/lib/mappers/cart";
import type {
  CartDto,
  CartTotalsDto,
  CartItemPricingDto,
} from "@/lib/api/cart";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makePricingTier(net: string, gross: string, tax: string) {
  return { net, gross, tax, currency: "EUR", tax_rate: "23" };
}

function makeItemPricing(
  undiscountedGross: string,
  discountedGross: string,
  discountAmountNet: string = "0.00",
  promoCode: string | null = null,
): CartItemPricingDto {
  const undiscountedNet = String((Number(undiscountedGross) / 1.23).toFixed(2));
  const discountedNet = String((Number(discountedGross) / 1.23).toFixed(2));
  return {
    undiscounted: makePricingTier(undiscountedNet, undiscountedGross, "0.00"),
    discounted: makePricingTier(discountedNet, discountedGross, "0.00"),
    discount: {
      amount_net: discountAmountNet,
      amount_gross: "0.00",
      percentage: discountAmountNet !== "0.00" ? "10.00" : "0",
      promotion_code: promoCode,
      promotion_type: promoCode ? "PERCENT" : null,
    },
  };
}

function makeTotals(overrides: Partial<CartTotalsDto> = {}): CartTotalsDto {
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

function makeDto(overrides: Partial<CartDto> = {}): CartDto {
  return {
    id: 1,
    status: "ACTIVE",
    items: [
      {
        id: 10,
        product: { id: 42, name: "Widget", price: "99.99" },
        quantity: 1,
        price_at_add_time: "99.99",
      },
    ],
    totals: makeTotals(),
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Backend totals integration
// ---------------------------------------------------------------------------

describe("mapCartToVm — with backend totals", () => {
  it("uses subtotal_undiscounted as subtotal", () => {
    const dto = makeDto({
      totals: makeTotals({
        subtotal_undiscounted: "200.00",
        total_gross: "180.00",
      }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.subtotal).toBe("200.00");
  });

  it("uses total_gross as total", () => {
    const dto = makeDto({
      totals: makeTotals({ total_gross: "180.00" }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.total).toBe("180.00");
  });

  it("uses currency from totals", () => {
    const dto = makeDto({ totals: makeTotals({ currency: "USD" }) });
    const vm = mapCartToVm(dto);
    expect(vm.currency).toBe("USD");
  });

  it("populates tax when total_tax > 0", () => {
    const dto = makeDto({
      totals: makeTotals({ total_tax: "23.00" }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.tax).toBe("23.00");
  });

  it("omits tax when total_tax is 0", () => {
    const dto = makeDto({ totals: makeTotals({ total_tax: "0.00" }) });
    const vm = mapCartToVm(dto);
    expect(vm.tax).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Discount handling
// ---------------------------------------------------------------------------

describe("mapCartToVm — discount handling", () => {
  it("sets discount.amount when total_discount > 0", () => {
    const dto = makeDto({
      totals: makeTotals({
        subtotal_undiscounted: "100.00",
        subtotal_discounted: "90.00",
        total_discount: "10.00",
        total_gross: "90.00",
      }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.discount).toBeDefined();
    expect(vm.discount?.amount).toBe("10.00");
  });

  it("leaves discount undefined when total_discount is 0", () => {
    const dto = makeDto({ totals: makeTotals({ total_discount: "0.00" }) });
    const vm = mapCartToVm(dto);
    expect(vm.discount).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Item unitPrice from per-item pricing
// ---------------------------------------------------------------------------

describe("mapCartToVm — item unitPrice", () => {
  it("uses discounted gross from per-item pricing when available", () => {
    const dto = makeDto({
      items: [
        {
          id: 10,
          product: { id: 42, name: "Widget", price: "100.00" },
          quantity: 1,
          price_at_add_time: "100.00",
          pricing: makeItemPricing("100.00", "90.00", "10.00", "promo-10"),
        },
      ],
    });
    const vm = mapCartToVm(dto);
    expect(vm.items[0].unitPrice).toBe("90.00");
  });

  it("falls back to price_at_add_time when item pricing is absent", () => {
    const dto = makeDto({
      items: [
        {
          id: 10,
          product: { id: 42, name: "Widget", price: "75.00" },
          quantity: 1,
          price_at_add_time: "65.00",
          // no pricing field
        },
      ],
    });
    const vm = mapCartToVm(dto);
    expect(vm.items[0].unitPrice).toBe("65.00");
  });

  it("falls back to product.price when pricing and price_at_add_time are absent", () => {
    const dto: CartDto = {
      id: 1,
      status: "ACTIVE",
      items: [
        {
          id: 10,
          product: { id: 42, name: "Widget", price: "75.00" },
          quantity: 1,
          price_at_add_time: "",
          // no pricing field
        },
      ],
    };
    const vm = mapCartToVm(dto);
    // No totals → falls back to manual calculation; unitPrice from product.price
    expect(vm.items[0].unitPrice).toBe("75.00");
  });
});

// ---------------------------------------------------------------------------
// Item discount fields from per-item pricing
// ---------------------------------------------------------------------------

describe("mapCartToVm — item discount fields", () => {
  it("sets originalUnitPrice to undiscounted.gross when promo is active", () => {
    const dto = makeDto({
      items: [
        {
          id: 10,
          product: { id: 42, name: "Widget", price: "100.00" },
          quantity: 1,
          price_at_add_time: "100.00",
          pricing: makeItemPricing("100.00", "90.00", "10.00", "PROMO10"),
        },
      ],
    });
    const vm = mapCartToVm(dto);
    expect(vm.items[0].originalUnitPrice).toBe("100.00");
  });

  it("sets discountLabel for a PERCENT-type active promotion", () => {
    const dto = makeDto({
      items: [
        {
          id: 10,
          product: { id: 42, name: "Widget", price: "100.00" },
          quantity: 1,
          price_at_add_time: "100.00",
          pricing: {
            undiscounted: {
              net: "81.30",
              gross: "100.00",
              tax: "0.00",
              currency: "EUR",
              tax_rate: "23",
            },
            discounted: {
              net: "73.17",
              gross: "90.00",
              tax: "0.00",
              currency: "EUR",
              tax_rate: "23",
            },
            discount: {
              amount_net: "8.13",
              amount_gross: "10.00",
              percentage: "10.00",
              promotion_code: "PROMO10",
              promotion_type: "PERCENT",
            },
          },
        },
      ],
    });
    const vm = mapCartToVm(dto);
    // Cart mapper uses en-dash (\u2013) for the label
    expect(vm.items[0].discountLabel).toBe("\u201310%");
  });

  it("returns undefined originalUnitPrice when no promotion is active", () => {
    const dto = makeDto({
      items: [
        {
          id: 10,
          product: { id: 42, name: "Widget", price: "100.00" },
          quantity: 1,
          price_at_add_time: "100.00",
          pricing: makeItemPricing("100.00", "100.00", "0.00", null),
        },
      ],
    });
    const vm = mapCartToVm(dto);
    expect(vm.items[0].originalUnitPrice).toBeUndefined();
  });

  it("returns undefined discountLabel when no promotion is active", () => {
    const dto = makeDto({
      items: [
        {
          id: 10,
          product: { id: 42, name: "Widget", price: "100.00" },
          quantity: 1,
          price_at_add_time: "100.00",
          pricing: makeItemPricing("100.00", "100.00", "0.00", null),
        },
      ],
    });
    const vm = mapCartToVm(dto);
    expect(vm.items[0].discountLabel).toBeUndefined();
  });

  it("returns undefined originalUnitPrice when item has no pricing", () => {
    const dto = makeDto();
    const vm = mapCartToVm(dto);
    expect(vm.items[0].originalUnitPrice).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Empty cart
// ---------------------------------------------------------------------------

describe("mapCartToVm — empty cart", () => {
  it("maps safely with zero totals", () => {
    const dto: CartDto = {
      id: 2,
      status: "ACTIVE",
      items: [],
      totals: makeTotals({
        subtotal_undiscounted: "0.00",
        subtotal_discounted: "0.00",
        total_discount: "0.00",
        total_tax: "0.00",
        total_gross: "0.00",
        currency: "EUR",
        item_count: 0,
      }),
    };
    const vm = mapCartToVm(dto);
    expect(vm.items).toHaveLength(0);
    expect(vm.subtotal).toBe("0.00");
    expect(vm.total).toBe("0.00");
    expect(vm.discount).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Legacy response (no totals field) — backward compat
// ---------------------------------------------------------------------------

describe("mapCartToVm — legacy response without totals", () => {
  it("computes subtotal and total manually", () => {
    const dto: CartDto = {
      id: 3,
      status: "ACTIVE",
      items: [
        {
          id: 11,
          product: { id: 1, name: "A", price: "10.00" },
          quantity: 2,
          price_at_add_time: "10.00",
        },
      ],
      // no totals
    };
    const vm = mapCartToVm(dto);
    expect(vm.subtotal).toBe("20.00");
    expect(vm.total).toBe("20.00");
    expect(vm.discount).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Phase 4 / Slice 3: order-level discount mapping
// ---------------------------------------------------------------------------

describe("mapCartToVm — order-level discount (Phase 4 / Slice 3)", () => {
  function makeTotalsWithOrderDiscount(
    overrides: Partial<CartTotalsDto> = {},
  ): CartTotalsDto {
    return makeTotals({
      total_gross: "100.00",
      total_tax: "18.70",
      order_discount_applied: true,
      order_discount_amount: "10.00",
      order_discount_promotion_code: "AUTO10",
      order_discount_promotion_name: "Spring Discount",
      total_gross_after_order_discount: "90.00",
      total_tax_after_order_discount: "16.83",
      ...overrides,
    });
  }

  it("populates orderDiscount when order_discount_applied is true", () => {
    const dto = makeDto({ totals: makeTotalsWithOrderDiscount() });
    const vm = mapCartToVm(dto);
    expect(vm.orderDiscount).toBeDefined();
  });

  it("maps promotionName from order_discount_promotion_name", () => {
    const dto = makeDto({ totals: makeTotalsWithOrderDiscount() });
    const vm = mapCartToVm(dto);
    expect(vm.orderDiscount?.promotionName).toBe("Spring Discount");
  });

  it("maps amount from order_discount_amount", () => {
    const dto = makeDto({ totals: makeTotalsWithOrderDiscount() });
    const vm = mapCartToVm(dto);
    expect(vm.orderDiscount?.amount).toBe("10.00");
  });

  it("maps totalGrossAfter from total_gross_after_order_discount", () => {
    const dto = makeDto({ totals: makeTotalsWithOrderDiscount() });
    const vm = mapCartToVm(dto);
    expect(vm.orderDiscount?.totalGrossAfter).toBe("90.00");
  });

  it("maps totalTaxAfter from total_tax_after_order_discount", () => {
    const dto = makeDto({ totals: makeTotalsWithOrderDiscount() });
    const vm = mapCartToVm(dto);
    expect(vm.orderDiscount?.totalTaxAfter).toBe("16.83");
  });

  it("uses totalGrossAfter as the cart total when order discount is applied", () => {
    const dto = makeDto({ totals: makeTotalsWithOrderDiscount() });
    const vm = mapCartToVm(dto);
    expect(vm.total).toBe("90.00");
  });

  it("uses totalTaxAfter as the cart tax when order discount is applied and tax > 0", () => {
    const dto = makeDto({ totals: makeTotalsWithOrderDiscount() });
    const vm = mapCartToVm(dto);
    expect(vm.tax).toBe("16.83");
  });

  it("omits tax when totalTaxAfter is 0.00 even after order discount", () => {
    const dto = makeDto({
      totals: makeTotalsWithOrderDiscount({
        total_tax_after_order_discount: "0.00",
      }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.tax).toBeUndefined();
  });

  it("leaves orderDiscount undefined when order_discount_applied is false", () => {
    const dto = makeDto({
      totals: makeTotals({ order_discount_applied: false }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.orderDiscount).toBeUndefined();
  });

  it("leaves orderDiscount undefined when totals field is absent", () => {
    const dto: CartDto = {
      id: 1,
      status: "ACTIVE",
      items: [],
    };
    const vm = mapCartToVm(dto);
    expect(vm.orderDiscount).toBeUndefined();
  });

  it("falls back to total_gross as the cart total when no order discount", () => {
    const dto = makeDto({
      totals: makeTotals({ total_gross: "120.00" }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.total).toBe("120.00");
  });

  it("orderDiscount and line-level discount can coexist", () => {
    const dto = makeDto({
      totals: makeTotalsWithOrderDiscount({
        total_discount: "5.00",
        subtotal_undiscounted: "100.00",
        subtotal_discounted: "95.00",
      }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.discount).toBeDefined();
    expect(vm.orderDiscount).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Phase 4 / Slice 4: threshold reward mapping
// ---------------------------------------------------------------------------

describe("mapCartToVm — threshold reward (Phase 4 / Slice 4)", () => {
  function makeTotalsWithThresholdReward(
    trOverrides: Partial<NonNullable<CartTotalsDto["threshold_reward"]>> = {},
    totalsOverrides: Partial<CartTotalsDto> = {},
  ): CartTotalsDto {
    return makeTotals({
      threshold_reward: {
        is_unlocked: false,
        promotion_name: "Free Shipping",
        threshold: "100.00",
        current_basis: "60.00",
        remaining: "40.00",
        currency: "EUR",
        ...trOverrides,
      },
      ...totalsOverrides,
    });
  }

  it("maps thresholdReward when threshold_reward is present", () => {
    const dto = makeDto({ totals: makeTotalsWithThresholdReward() });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward).toBeDefined();
  });

  it("maps isUnlocked correctly for locked state", () => {
    const dto = makeDto({
      totals: makeTotalsWithThresholdReward({ is_unlocked: false }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward?.isUnlocked).toBe(false);
  });

  it("maps isUnlocked correctly for unlocked state", () => {
    const dto = makeDto({
      totals: makeTotalsWithThresholdReward({
        is_unlocked: true,
        remaining: "0.00",
      }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward?.isUnlocked).toBe(true);
  });

  it("maps remaining from threshold_reward.remaining", () => {
    const dto = makeDto({
      totals: makeTotalsWithThresholdReward({ remaining: "25.50" }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward?.remaining).toBe("25.50");
  });

  it("maps promotionName from threshold_reward.promotion_name", () => {
    const dto = makeDto({
      totals: makeTotalsWithThresholdReward({ promotion_name: "Gold Tier" }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward?.promotionName).toBe("Gold Tier");
  });

  it("maps currentBasis from threshold_reward.current_basis", () => {
    const dto = makeDto({
      totals: makeTotalsWithThresholdReward({ current_basis: "80.00" }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward?.currentBasis).toBe("80.00");
  });

  it("maps threshold from threshold_reward.threshold", () => {
    const dto = makeDto({
      totals: makeTotalsWithThresholdReward({ threshold: "150.00" }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward?.threshold).toBe("150.00");
  });

  it("leaves thresholdReward undefined when threshold_reward is null", () => {
    const dto = makeDto({
      totals: makeTotals({ threshold_reward: null }),
    });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward).toBeUndefined();
  });

  it("leaves thresholdReward undefined when threshold_reward is absent", () => {
    const dto = makeDto({ totals: makeTotals() });
    const vm = mapCartToVm(dto);
    expect(vm.thresholdReward).toBeUndefined();
  });
});
