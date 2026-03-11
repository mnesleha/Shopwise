import type { OrderDto, OrderItemDto } from "@/lib/api/orders";
import type { OrderViewModel, OrderItem, VatBreakdownLine } from "@/components/order/OrderDetail";

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
  name: "Customer (missing in API)",
  addressLine1: "—",
  city: "—",
  postalCode: "—",
  country: "—",
  email: "—",
  phone: "—",
};

function formatOrderNumber(orderId: number): string {
  // simple demo formatting; replace once backend provides real order number
  const year = new Date().getFullYear();
  return `OBJ${year}${String(orderId).padStart(6, "0")}`;
}

function buildDiscountNote(dto: OrderItemDto): string | null {
  if (!dto.discount) return null;
  if (dto.discount.type === "PERCENT") {
    return `Includes line discount ${dto.discount.value}%`;
  }
  return `Includes line discount ${dto.discount.value}`;
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

export function mapOrderToVm(dto: OrderDto): OrderViewModel {
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
    customer: DEFAULT_CUSTOMER,

    shippingMethod: "Standard (simulated)",
    paymentMethod: "Card (simulated)",
    barcodeValue: orderNumber,

    items: dto.items.map(mapItem),

    // Phase 3 totals snapshot
    subtotalNet: dto.subtotal_net ?? null,
    subtotalGross: dto.subtotal_gross ?? null,
    totalTax: dto.total_tax ?? null,
    totalDiscount: dto.total_discount ?? null,
    currency: dto.currency ?? "EUR",
    vatBreakdown,

    // Legacy total kept for backward compat
    total: dto.subtotal_gross ?? dto.total,
  };
}

