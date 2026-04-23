/**
 * OrdersMapper unit tests
 *
 * Contract guarded:
 * - product_name snapshot is used as productName when provided
 * - Falls back to "Product #N" when product_name is null (pre-snapshot record)
 * - discountNote is "Line discount: N%" for PERCENT discounts (rounded)
 * - discountNote derives effective percentage for FIXED discounts (from snapshot price)
 * - discountNote rounds fractional percentages to nearest whole number
 * - discountNote is null when no discount
 * - Phase 3 invoice fields are mapped to the view model
 * - vat_breakdown is mapped to VatBreakdownLine[]
 * - vat_breakdown: null becomes null in the VM
 * - createdAt is mapped from created_at ISO string
 * - total maps to dto.total (the actual final total after all discounts)
 * - subtotalGross maps to dto.subtotal_gross (gross subtotal before order discount)
 * - order-level totals (subtotalNet, subtotalGross, totalTax, totalDiscount) are mapped
 * - Phase 4: subtotalGross prefers pre_order_discount_subtotal_gross when present
 * - Phase 4: total prefers post_order_discount_total_gross when present
 * - Phase 4: subtotalNet prefers post_order_discount_subtotal_net when present
 * - Phase 4: totalTax prefers post_order_discount_total_tax when present
 * - Phase 4: orderDiscountGross is mapped from order_discount_gross
 * - Phase 4: orderDiscountGross is null when order_discount_gross is absent
 */

import { describe, it, expect } from "vitest";
import { mapOrderToVm } from "@/lib/mappers/orders";
import type { OrderDto, OrderItemDto } from "@/lib/api/orders";

// ── Helpers ─────────────────────────────────────────────────────────────────

function makeItemDto(overrides: Partial<OrderItemDto> = {}): OrderItemDto {
  return {
    id: 1,
    product: 10,
    product_name: "Test Mouse",
    quantity: 2,
    unit_price: "29.99",
    unit_price_net: "27.02",
    unit_price_gross: "29.99",
    tax_amount: "2.97",
    tax_rate: "10.99",
    line_total: "59.98",
    line_total_net: "54.04",
    line_total_gross: "59.98",
    discount: null,
    ...overrides,
  };
}

function makeOrderDto(overrides: Partial<OrderDto> = {}): OrderDto {
  return {
    id: 42,
    status: "CREATED",
    created_at: "2026-02-25T10:00:00Z",
    items: [makeItemDto()],
    total: "59.98",
    subtotal_net: "54.04",
    subtotal_gross: "59.98",
    total_tax: "5.94",
    total_discount: null,
    currency: "EUR",
    vat_breakdown: null,
    ...overrides,
  };
}

// ── Product name snapshot ─────────────────────────────────────────────────

describe("mapOrderToVm — product name snapshot", () => {
  it("uses product_name when provided", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ product_name: "Wireless Keyboard" })],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].productName).toBe("Wireless Keyboard");
  });

  it("falls back to 'Product #N' when product_name is null", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ product: 99, product_name: null })],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].productName).toBe("Product #99");
  });

  it("falls back to 'Product #N' when product_name is undefined", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ product: 7, product_name: undefined })],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].productName).toBe("Product #7");
  });
});

// ── Discount note ─────────────────────────────────────────────────────────

describe("mapOrderToVm — discountNote", () => {
  it("returns null when no discount", () => {
    const dto = makeOrderDto({ items: [makeItemDto({ discount: null })] });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].discountNote).toBeNull();
  });

  it("PERCENT: formats as 'Line discount: N%' with rounded whole number", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ discount: { type: "PERCENT", value: "10" } })],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].discountNote).toBe("Line discount: 10%");
  });

  it("PERCENT: rounds fractional discount values", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ discount: { type: "PERCENT", value: "10.75" } })],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].discountNote).toBe("Line discount: 11%");
  });

  it("FIXED: derives effective percentage from snapshot unit_price_gross", () => {
    // unit_price_gross = 20.00, fixed discount = 5.00 → original = 25.00
    // effective% = 5/25 = 20%
    const dto = makeOrderDto({
      items: [
        makeItemDto({
          unit_price_gross: "20.00",
          discount: { type: "FIXED", value: "5.00" },
        }),
      ],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].discountNote).toBe("Line discount: 20%");
  });

  it("FIXED: falls back to unit_price when unit_price_gross is null", () => {
    // unit_price = 24.00, fixed discount = 6.00 → original = 30.00
    // effective% = 6/30 = 20%
    const dto = makeOrderDto({
      items: [
        makeItemDto({
          unit_price: "24.00",
          unit_price_gross: null,
          discount: { type: "FIXED", value: "6.00" },
        }),
      ],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].discountNote).toBe("Line discount: 20%");
  });

  it("FIXED: rounds derived effective percentage", () => {
    // unit_price_gross = 29.99, fixed discount = 5.00 → original = 34.99
    // effective% = 5/34.99 ≈ 14.3% → 14%
    const dto = makeOrderDto({
      items: [
        makeItemDto({
          unit_price_gross: "29.99",
          discount: { type: "FIXED", value: "5.00" },
        }),
      ],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.items[0].discountNote).toBe("Line discount: 14%");
  });
});

// ── Phase 3 invoice item fields ───────────────────────────────────────────

describe("mapOrderToVm — invoice item fields", () => {
  it("maps unitPriceNet from unit_price_net", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ unit_price_net: "27.02" })],
    });
    expect(mapOrderToVm(dto).items[0].unitPriceNet).toBe("27.02");
  });

  it("sets unitPriceNet to null when unit_price_net is absent", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ unit_price_net: null })],
    });
    expect(mapOrderToVm(dto).items[0].unitPriceNet).toBeNull();
  });

  it("maps taxRate from tax_rate", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ tax_rate: "10.00" })],
    });
    expect(mapOrderToVm(dto).items[0].taxRate).toBe("10.00");
  });

  it("maps taxAmount from tax_amount", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ tax_amount: "2.97" })],
    });
    expect(mapOrderToVm(dto).items[0].taxAmount).toBe("2.97");
  });

  it("maps lineTotalNet from line_total_net", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ line_total_net: "54.04" })],
    });
    expect(mapOrderToVm(dto).items[0].lineTotalNet).toBe("54.04");
  });

  it("maps lineTotalGross from line_total_gross", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ line_total_gross: "59.98" })],
    });
    expect(mapOrderToVm(dto).items[0].lineTotalGross).toBe("59.98");
  });

  it("falls back lineTotalGross to line_total when line_total_gross is null", () => {
    const dto = makeOrderDto({
      items: [makeItemDto({ line_total: "59.98", line_total_gross: null })],
    });
    expect(mapOrderToVm(dto).items[0].lineTotalGross).toBe("59.98");
  });
});

// ── Order-level totals ────────────────────────────────────────────────────

describe("mapOrderToVm — order-level totals", () => {
  it("maps subtotalNet from subtotal_net", () => {
    const dto = makeOrderDto({ subtotal_net: "54.04" });
    expect(mapOrderToVm(dto).subtotalNet).toBe("54.04");
  });

  it("maps subtotalGross from subtotal_gross", () => {
    const dto = makeOrderDto({ subtotal_gross: "59.98" });
    expect(mapOrderToVm(dto).subtotalGross).toBe("59.98");
  });

  it("maps totalTax from total_tax", () => {
    const dto = makeOrderDto({ total_tax: "5.94" });
    expect(mapOrderToVm(dto).totalTax).toBe("5.94");
  });

  it("maps totalDiscount from total_discount", () => {
    const dto = makeOrderDto({ total_discount: "3.00" });
    expect(mapOrderToVm(dto).totalDiscount).toBe("3.00");
  });

  it("maps total from dto.total (the actual final total after all discounts)", () => {
    // subtotal_gross is the pre-order-discount subtotal; dto.total is the real total
    const dto = makeOrderDto({ subtotal_gross: "59.98", total: "55.00" });
    expect(mapOrderToVm(dto).total).toBe("55.00");
  });

  it("maps subtotalGross separately from total", () => {
    const dto = makeOrderDto({ subtotal_gross: "59.98", total: "55.00" });
    expect(mapOrderToVm(dto).subtotalGross).toBe("59.98");
  });

  it("sets subtotalGross to null when subtotal_gross is null", () => {
    const dto = makeOrderDto({ subtotal_gross: null, total: "55.00" });
    expect(mapOrderToVm(dto).subtotalGross).toBeNull();
    expect(mapOrderToVm(dto).total).toBe("55.00");
  });

  // ── Phase 4: explicit pre/post order-discount fields ───────────────────

  it("subtotalGross prefers pre_order_discount_subtotal_gross when present", () => {
    const dto = makeOrderDto({
      pre_order_discount_subtotal_gross: "110.00",
      subtotal_gross: "99.00",
    });
    expect(mapOrderToVm(dto).subtotalGross).toBe("110.00");
  });

  it("subtotalGross falls back to subtotal_gross when pre_order_discount_subtotal_gross absent", () => {
    const dto = makeOrderDto({ subtotal_gross: "59.98" });
    expect(mapOrderToVm(dto).subtotalGross).toBe("59.98");
  });

  it("total prefers post_order_discount_total_gross when present", () => {
    const dto = makeOrderDto({
      post_order_discount_total_gross: "99.00",
      total: "110.00",
    });
    expect(mapOrderToVm(dto).total).toBe("99.00");
  });

  it("total falls back to dto.total when post_order_discount_total_gross absent", () => {
    const dto = makeOrderDto({ total: "59.98" });
    expect(mapOrderToVm(dto).total).toBe("59.98");
  });

  it("subtotalNet prefers post_order_discount_subtotal_net when present", () => {
    const dto = makeOrderDto({
      post_order_discount_subtotal_net: "90.00",
      subtotal_net: "100.00",
    });
    expect(mapOrderToVm(dto).subtotalNet).toBe("90.00");
  });

  it("totalTax prefers post_order_discount_total_tax when present", () => {
    const dto = makeOrderDto({
      post_order_discount_total_tax: "9.00",
      total_tax: "10.00",
    });
    expect(mapOrderToVm(dto).totalTax).toBe("9.00");
  });

  it("maps orderDiscountGross from order_discount_gross", () => {
    const dto = makeOrderDto({ order_discount_gross: "11.00" });
    expect(mapOrderToVm(dto).orderDiscountGross).toBe("11.00");
  });

  it("sets orderDiscountGross to null when order_discount_gross is absent", () => {
    const dto = makeOrderDto();
    expect(mapOrderToVm(dto).orderDiscountGross).toBeNull();
  });

  it("sets orderDiscountGross to null when order_discount_gross is explicitly null", () => {
    const dto = makeOrderDto({ order_discount_gross: null });
    expect(mapOrderToVm(dto).orderDiscountGross).toBeNull();
  });
});

describe("mapOrderToVm — shipping summary", () => {
  it("maps shipping method and shipment summary from backend data", () => {
    const dto = makeOrderDto({
      payment_method: "COD",
      shipping_method: {
        provider_code: "MOCK",
        service_code: "express",
        name: "Express",
      },
      shipment_summary: {
        status: "IN_TRANSIT",
        tracking_number: "MOCK-123-EXPRESS",
        label_url: "https://mock-shipping.local/labels/MOCK-123-EXPRESS",
      },
    });

    const vm = mapOrderToVm(dto);

    expect(vm.shippingMethod).toBe("Express");
    expect(vm.shipmentStatus).toBe("IN_TRANSIT");
    expect(vm.trackingNumber).toBe("MOCK-123-EXPRESS");
    expect(vm.shippingLabelUrl).toBe(
      "https://mock-shipping.local/labels/MOCK-123-EXPRESS",
    );
    expect(vm.paymentMethod).toBe("Cash on delivery");
  });

  it("maps CARD payment method into a readable label", () => {
    const dto = makeOrderDto({ payment_method: "CARD" });

    expect(mapOrderToVm(dto).paymentMethod).toBe("Card");
  });

  it("maps shipment timeline entries", () => {
    const dto = makeOrderDto({
      shipment_timeline: [
        {
          status: "PENDING",
          label: "Pending",
          occurred_at: "2026-03-28T16:00:00Z",
          is_current: false,
        },
        {
          status: "IN_TRANSIT",
          label: "In transit",
          occurred_at: "2026-03-29T08:15:00Z",
          is_current: true,
        },
      ],
    });

    expect(mapOrderToVm(dto).shipmentTimeline).toEqual([
      {
        status: "PENDING",
        label: "Pending",
        occurredAt: "2026-03-28T16:00:00Z",
        isCurrent: false,
      },
      {
        status: "IN_TRANSIT",
        label: "In transit",
        occurredAt: "2026-03-29T08:15:00Z",
        isCurrent: true,
      },
    ]);
  });
});

// ── VAT breakdown mapping ─────────────────────────────────────────────────

describe("mapOrderToVm — vat_breakdown", () => {
  it("maps vat_breakdown rows to VatBreakdownLine[]", () => {
    const dto = makeOrderDto({
      vat_breakdown: [
        {
          tax_rate: "10.00",
          tax_base: "100.00",
          vat_amount: "10.00",
          total_incl_vat: "110.00",
        },
      ],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.vatBreakdown).toEqual([
      {
        taxRate: "10.00",
        taxBase: "100.00",
        vatAmount: "10.00",
        totalInclVat: "110.00",
      },
    ]);
  });

  it("sets vatBreakdown to null when vat_breakdown is null", () => {
    const dto = makeOrderDto({ vat_breakdown: null });
    expect(mapOrderToVm(dto).vatBreakdown).toBeNull();
  });

  it("passes through multiple VAT rate rows in order", () => {
    const dto = makeOrderDto({
      vat_breakdown: [
        {
          tax_rate: "10.00",
          tax_base: "100.00",
          vat_amount: "10.00",
          total_incl_vat: "110.00",
        },
        {
          tax_rate: "21.00",
          tax_base: "50.00",
          vat_amount: "10.50",
          total_incl_vat: "60.50",
        },
      ],
    });
    const vm = mapOrderToVm(dto);
    expect(vm.vatBreakdown).toHaveLength(2);
    expect(vm.vatBreakdown![0].taxRate).toBe("10.00");
    expect(vm.vatBreakdown![1].taxRate).toBe("21.00");
  });
});

// ── createdAt ─────────────────────────────────────────────────────────────

describe("mapOrderToVm — createdAt", () => {
  it("maps created_at ISO string to a localeDateString", () => {
    const dto = makeOrderDto({ created_at: "2026-02-25T12:00:00Z" });
    const vm = mapOrderToVm(dto);
    // The result should be a non-empty date string
    expect(typeof vm.createdAt).toBe("string");
    expect(vm.createdAt!.length).toBeGreaterThan(0);
  });
});
