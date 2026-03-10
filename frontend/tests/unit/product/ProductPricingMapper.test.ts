/**
 * ProductPricingMapper — unit tests
 *
 * Covers:
 * - mapProductToGridItem: discount fields populated when pricing has an active promo
 * - mapProductToGridItem: no discount fields when pricing is null or promo absent
 * - mapProductToDetailVm: same discount field logic
 * - buildDiscountLabel: PERCENT, FIXED amount, no active promo
 */

import { describe, it, expect } from "vitest";
import {
  mapProductToGridItem,
  mapProductToDetailVm,
} from "@/lib/mappers/products";
import type {
  ProductListItemDto,
  ProductDetailDto,
  ProductPricingDto,
} from "@/lib/mappers/products";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makePricingTier(gross: string, net: string) {
  return { gross, net, tax: "0.00", currency: "EUR", tax_rate: "23" };
}

function makeDiscount(
  opts: {
    promoCode?: string | null;
    promoType?: string | null;
    percentage?: string | null;
    amountGross?: string;
    amountNet?: string;
    amountScope?: string | null;
  } = {},
) {
  return {
    amount_net: opts.amountNet ?? "0.00",
    amount_gross: opts.amountGross ?? "0.00",
    percentage: opts.percentage ?? null,
    promotion_code: opts.promoCode ?? null,
    promotion_type: opts.promoType ?? null,
    amount_scope: opts.amountScope ?? null,
  };
}

function makePricing(
  undiscountedGross: string,
  discountedGross: string,
  discount: ReturnType<typeof makeDiscount>,
): ProductPricingDto {
  return {
    undiscounted: makePricingTier(undiscountedGross, "0.00"),
    discounted: makePricingTier(discountedGross, "0.00"),
    discount,
  };
}

function makeListItemDto(
  pricing: ProductPricingDto | null = null,
): ProductListItemDto {
  return {
    id: 1,
    name: "Widget",
    price: "100.00",
    stock_quantity: 5,
    short_description: "A widget",
    stock_status: "IN_STOCK",
    primary_image: null,
    pricing,
  };
}

function makeDetailDto(
  pricing: ProductPricingDto | null = null,
): ProductDetailDto {
  return {
    id: 1,
    name: "Widget",
    price: "100.00",
    stock_quantity: 5,
    short_description: "A widget",
    full_description: "Full text",
    primary_image: null,
    gallery_images: [],
    pricing,
  };
}

// ---------------------------------------------------------------------------
// mapProductToGridItem — no discount
// ---------------------------------------------------------------------------

describe("mapProductToGridItem — no discount", () => {
  it("returns undefined discountedPrice when pricing is null", () => {
    const vm = mapProductToGridItem(makeListItemDto(null));
    expect(vm.discountedPrice).toBeUndefined();
  });

  it("returns undefined originalPrice when pricing is null", () => {
    const vm = mapProductToGridItem(makeListItemDto(null));
    expect(vm.originalPrice).toBeUndefined();
  });

  it("returns undefined discountLabel when pricing is null", () => {
    const vm = mapProductToGridItem(makeListItemDto(null));
    expect(vm.discountLabel).toBeUndefined();
  });

  it("uses dto.price as price when pricing is null", () => {
    const vm = mapProductToGridItem(makeListItemDto(null));
    expect(vm.price).toBe("100.00");
  });

  it("returns undefined discountLabel when no promotion_code", () => {
    const pricing = makePricing(
      "100.00",
      "100.00",
      makeDiscount({ promoCode: null }),
    );
    const vm = mapProductToGridItem(makeListItemDto(pricing));
    expect(vm.discountLabel).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// mapProductToGridItem — PERCENT discount
// ---------------------------------------------------------------------------

describe("mapProductToGridItem — PERCENT discount", () => {
  function makePercentPricing() {
    return makePricing(
      "100.00",
      "90.00",
      makeDiscount({
        promoCode: "SAVE10",
        promoType: "PERCENT",
        percentage: "10.00",
        amountGross: "10.00",
        amountNet: "8.13",
      }),
    );
  }

  it("sets discountedPrice to discounted.gross", () => {
    const vm = mapProductToGridItem(makeListItemDto(makePercentPricing()));
    expect(vm.discountedPrice).toBe("90.00");
  });

  it("sets originalPrice to undiscounted.gross", () => {
    const vm = mapProductToGridItem(makeListItemDto(makePercentPricing()));
    expect(vm.originalPrice).toBe("100.00");
  });

  it("sets discountLabel to '–10%'", () => {
    const vm = mapProductToGridItem(makeListItemDto(makePercentPricing()));
    expect(vm.discountLabel).toBe("–10%");
  });

  it("sets price to the discounted gross", () => {
    const vm = mapProductToGridItem(makeListItemDto(makePercentPricing()));
    expect(vm.price).toBe("90.00");
  });
});

// ---------------------------------------------------------------------------
// mapProductToGridItem — FIXED discount
// ---------------------------------------------------------------------------

describe("mapProductToGridItem — FIXED discount", () => {
  function makeFixedPricing() {
    return makePricing(
      "50.00",
      "45.00",
      makeDiscount({
        promoCode: "FIXED5",
        promoType: "FIXED",
        percentage: null,
        amountGross: "5.00",
        amountNet: "4.07",
        amountScope: "GROSS",
      }),
    );
  }

  it("sets discountLabel using amount_gross with currency symbol", () => {
    const vm = mapProductToGridItem(makeListItemDto(makeFixedPricing()));
    // currency defaults to "USD" in the mapper
    expect(vm.discountLabel).toBe("–$\u00a05.00");
  });

  it("sets discountedPrice correctly", () => {
    const vm = mapProductToGridItem(makeListItemDto(makeFixedPricing()));
    expect(vm.discountedPrice).toBe("45.00");
  });
});

// ---------------------------------------------------------------------------
// mapProductToDetailVm — discount fields
// ---------------------------------------------------------------------------

describe("mapProductToDetailVm — discount fields", () => {
  function makePercentPricing() {
    return makePricing(
      "200.00",
      "170.00",
      makeDiscount({
        promoCode: "SUMMER15",
        promoType: "PERCENT",
        percentage: "15.00",
        amountGross: "30.00",
      }),
    );
  }

  it("sets discountedPrice when promo active", () => {
    const vm = mapProductToDetailVm(makeDetailDto(makePercentPricing()));
    expect(vm.discountedPrice).toBe("170.00");
  });

  it("sets originalPrice when promo active", () => {
    const vm = mapProductToDetailVm(makeDetailDto(makePercentPricing()));
    expect(vm.originalPrice).toBe("200.00");
  });

  it("sets discountLabel to '–15%'", () => {
    const vm = mapProductToDetailVm(makeDetailDto(makePercentPricing()));
    expect(vm.discountLabel).toBe("–15%");
  });

  it("returns undefined discountedPrice when no pricing", () => {
    const vm = mapProductToDetailVm(makeDetailDto(null));
    expect(vm.discountedPrice).toBeUndefined();
  });
});
