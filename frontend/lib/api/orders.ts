import { api } from "@/lib/api";

export type VatBreakdownDto = {
  tax_rate: string;       // e.g. "10.00" (percentage)
  tax_base: string;       // sum of net line totals for this rate
  vat_amount: string;     // sum of (gross - net) for this rate
  total_incl_vat: string; // sum of gross line totals for this rate
};

export type OrderItemDto = {
  id: number;
  product: number;
  /** Snapshot of the product name at order time. Null for pre-snapshot orders. */
  product_name: string | null;
  quantity: number;
  /** Gross unit price (backward-compat legacy field) */
  unit_price: string;
  /** Net unit price excl. VAT — null for pre-snapshot / unmigrated products */
  unit_price_net: string | null;
  /** Gross unit price incl. VAT — explicit Phase 3 field */
  unit_price_gross: string | null;
  /** Per-unit VAT amount */
  tax_amount: string | null;
  /** Effective tax rate percentage, e.g. "10.00" */
  tax_rate: string | null;
  /** Gross line total (backward-compat legacy field) */
  line_total: string;
  /** Net line total (unit_net × qty) */
  line_total_net: string | null;
  /** Gross line total (unit_gross × qty) */
  line_total_gross: string | null;
  discount: null | {
    type: "FIXED" | "PERCENT";
    value: string;
  };
};

export type BaseOrderDto = {
  id: number;
  status: string;
  /** ISO 8601 timestamp, e.g. "2026-03-11T10:00:00Z" */
  created_at: string | null;
  items: OrderItemDto[];
  /** Gross order total (backward-compat) */
  total: string;
  /** Net subtotal excl. VAT */
  subtotal_net: string | null;
  /** Gross subtotal incl. VAT */
  subtotal_gross: string | null;
  total_tax: string | null;
  total_discount: string | null;
  currency: string | null;
  /** VAT breakdown grouped by tax rate — owned by backend, ready for invoice rendering */
  vat_breakdown: VatBreakdownDto[] | null;
  // Phase 4 — explicit pre/post order-discount fields.
  // These supersede the ambiguously-named snapshot fields above for any UI
  // that must distinguish order-level discount deductions.
  /** Gross order-level discount applied at checkout. Null when no OD was applied. */
  order_discount_gross?: string | null;
  /** Gross subtotal incl. VAT after line discounts, BEFORE the order-level discount. */
  pre_order_discount_subtotal_gross?: string | null;
  /** Post-OD net subtotal (tax base). Aliases subtotal_net, null for legacy orders. */
  post_order_discount_subtotal_net?: string | null;
  /** Post-OD total VAT. Aliases total_tax, null for legacy orders. */
  post_order_discount_total_tax?: string | null;
  /** Final gross total after all discounts. Aliases subtotal_gross (when populated). */
  post_order_discount_total_gross?: string | null;
};

export type OrderDto = BaseOrderDto;
export type GuestOrderDto = BaseOrderDto;

export async function getOrder(orderId: number): Promise<OrderDto> {
  const res = await api.get<OrderDto>(`/orders/${orderId}/`);
  return res.data;
}

/**
 * POST /orders/claim/
 *
 * Claims any guest orders that share the current user's email address.
 * Returns the number of orders that were claimed.
 * Requires authentication.
 */
export async function claimOrders(): Promise<{ claimed_orders: number }> {
  const res = await api.post<{ claimed_orders: number }>("/orders/claim/");
  return res.data;
}

