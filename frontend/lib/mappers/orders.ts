import type {
  OrderItemDto,
  AddressSnapshotDto,
  BaseOrderDto,
} from "@/lib/api/orders";
import type {
  OrderViewModel,
  OrderItem,
  VatBreakdownLine,
} from "@/components/order/OrderDetail";

const DEFAULT_SUPPLIER = {
  name: "Shopwise Demo Supplier Ltd.",
  addressLine1: "Demo Street 1",
  city: "Prague",
  postalCode: "110 00",
  country: "Czech Republic",
  companyId: "CZ12345678",
  vatId: "CZ12345678",
  email: "supplier@shopwise.demo",
  phone: "+420 000 000 000",
  bankAccount: {
    bankName: "Demo Bank",
    accountNumber: "000000-0000000000/0000",
    iban: "CZ0000000000000000000000",
    swift: "DEMOXXXX",
  },
};

const DEFAULT_CUSTOMER = {
  name: "—",
  addressLine1: "—",
  city: "—",
  postalCode: "—",
  country: "—",
};

const countryNames = new Intl.DisplayNames(["en"], { type: "region" });

function resolveCountry(code: string): string {
  if (!code) return "—";
  try {
    return countryNames.of(code) ?? code;
  } catch {
    return code;
  }
}

function mapAddressToCustomer(addr: AddressSnapshotDto, email?: string | null) {
  return {
    name:
      addr.name ||
      [addr.first_name, addr.last_name].filter(Boolean).join(" ") ||
      "—",
    addressLine1: addr.address_line1 || "—",
    addressLine2: addr.address_line2 || undefined,
    city: addr.city || "—",
    postalCode: addr.postal_code || "—",
    country: resolveCountry(addr.country),
    company: addr.company || undefined,
    companyId: addr.company_id || undefined,
    vatId: addr.vat_id || undefined,
    phone: addr.phone || undefined,
    email: email || undefined,
  };
}

function formatOrderNumber(orderId: number): string {
  // simple demo formatting; replace once backend provides real order number
  const year = new Date().getFullYear();
  return `OBJ${year}${String(orderId).padStart(6, "0")}`;
}

/**
 * Derive a customer-facing discount note for invoice display.
 *
 * Both PERCENT and FIXED promotions are normalised to an effective percentage
 * rounded to the nearest whole number (e.g. "Discount applied: 30%").  This
 * avoids showing a raw fixed-amount that has no meaning without the original
 * price — which the invoice view does not display.
 *
 * For FIXED discounts the effective rate is back-calculated from the snapshot:
 *   effective% = fixed_amount / (discounted_gross + fixed_amount) × 100
 */
function buildDiscountNote(dto: OrderItemDto): string | null {
  if (!dto.discount) return null;

  let effectivePct: number;

  if (dto.discount.type === "PERCENT") {
    effectivePct = Math.round(parseFloat(dto.discount.value));
  } else {
    // FIXED: the snapshot unit_price_gross is the post-discount price.
    // Reconstruct the original: original = discounted + fixed_amount.
    const discountedGross = parseFloat(dto.unit_price_gross ?? dto.unit_price);
    const fixedAmount = parseFloat(dto.discount.value);
    const originalGross = discountedGross + fixedAmount;
    if (!isFinite(originalGross) || originalGross <= 0) return null;
    effectivePct = Math.round((fixedAmount / originalGross) * 100);
  }

  return `Line discount: ${effectivePct}%`;
}

function mapItem(dto: OrderItemDto): OrderItem {
  return {
    id: String(dto.id),
    productId: String(dto.product),
    // Use the snapshot name captured at order time; fall back to a stable
    // placeholder only for pre-snapshot records where the field is null.
    productName: dto.product_name ?? `Product #${dto.product}`,
    productUrl: `/products/${dto.product}`,
    quantity: dto.quantity,
    // Legacy gross unit price kept for backward compat
    unitPrice: dto.unit_price,
    // Phase 3 invoice fields
    unitPriceNet: dto.unit_price_net ?? null,
    unitPriceGross: dto.unit_price_gross ?? dto.unit_price,
    taxAmount: dto.tax_amount ?? null,
    taxRate: dto.tax_rate ?? null,
    // Legacy gross line total kept for backward compat
    lineTotal: dto.line_total,
    lineTotalNet: dto.line_total_net ?? null,
    lineTotalGross: dto.line_total_gross ?? dto.line_total,
    // Neutral discount note for invoice display (no badge / strike-through)
    discountNote: buildDiscountNote(dto),
    // Keep raw discount for legacy callers
    discount: dto.discount,
  };
}

export function mapOrderToVm(dto: BaseOrderDto): OrderViewModel {
  const orderNumber = formatOrderNumber(dto.id);

  const vatBreakdown: VatBreakdownLine[] | null = dto.vat_breakdown
    ? dto.vat_breakdown.map((row) => ({
        taxRate: row.tax_rate,
        taxBase: row.tax_base,
        vatAmount: row.vat_amount,
        totalInclVat: row.total_incl_vat,
      }))
    : null;

  return {
    id: String(dto.id),
    orderNumber,
    status: dto.status,
    createdAt: dto.created_at
      ? new Date(dto.created_at).toLocaleDateString()
      : new Date().toLocaleDateString(),

    supplier: DEFAULT_SUPPLIER,
    // billing_address is null when billing_same_as_shipping; fall back to shipping.
    customer: dto.billing_address
      ? mapAddressToCustomer(dto.billing_address, dto.customer_email)
      : dto.shipping_address
        ? mapAddressToCustomer(dto.shipping_address, dto.customer_email)
        : DEFAULT_CUSTOMER,

    shippingMethod: "Standard (simulated)",
    paymentMethod: "Card (simulated)",
    barcodeValue: orderNumber,

    items: dto.items.map(mapItem),

    // Phase 3 totals snapshot (legacy field names, kept for backward compat).
    subtotalNet:
      dto.post_order_discount_subtotal_net ?? dto.subtotal_net ?? null,
    // subtotalGross = gross subtotal BEFORE order-level discount (pre-OD subtotal).
    // When the Phase 4 explicit field is present use it; otherwise fall back to
    // subtotal_gross (which, without an OD, equals the final total).
    subtotalGross:
      dto.pre_order_discount_subtotal_gross ?? dto.subtotal_gross ?? null,
    totalTax: dto.post_order_discount_total_tax ?? dto.total_tax ?? null,
    totalDiscount: dto.total_discount ?? null,
    // Phase 4: order-level discount only (does not include per-item line discounts).
    orderDiscountGross: dto.order_discount_gross ?? null,
    currency: dto.currency ?? "EUR",
    vatBreakdown,

    // Final gross total after all discounts (line-level + order-level).
    total: dto.post_order_discount_total_gross ?? dto.total,
  };
}
