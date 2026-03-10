import type { CartDto } from "@/lib/api/cart";

export type CartVm = {
  id: string;
  currency?: string;
  items: Array<{
    productId: string;
    productName: string;
    productUrl?: string;
    shortDescription?: string;
    unitPrice: string;
    quantity: number;
    stockQuantity?: number;
    imageUrl?: string;
    /** Original (undiscounted) unit gross price; present when a promotion applies. */
    originalUnitPrice?: string;
    /** Short discount label, e.g. "–10%". */
    discountLabel?: string;
  }>;
  discount?: {
    code?: string;
    description?: string;
    amount?: string;
  };
  subtotal: string;
  tax?: string;
  total: string;
};

function addDecimalStrings(a: string, b: string): string {
  // simple decimal sum using JS number; OK for demo UI
  // (later can be moved to backend / decimal library)
  const sum = (Number(a) || 0) + (Number(b) || 0);
  return sum.toFixed(2);
}

function mulDecimalString(a: string, qty: number): string {
  const v = (Number(a) || 0) * qty;
  return v.toFixed(2);
}

export function mapCartToVm(dto: CartDto): CartVm {
  const items = dto.items.map((it) => {
    const pricing = it.pricing;
    const hasDiscount = Boolean(
      pricing?.discount?.promotion_code &&
      pricing.discounted?.gross !== pricing.undiscounted?.gross,
    );
    const unitPrice =
      pricing?.discounted?.gross ?? (it.price_at_add_time || it.product.price);

    let discountLabel: string | undefined;
    if (hasDiscount && pricing?.discount) {
      const pct = pricing.discount.percentage;
      if (pct && pct !== "0" && pct !== "0.00") {
        const rounded = Math.round(parseFloat(pct));
        discountLabel = `\u2013${rounded}%`;
      } else {
        const gross = pricing.discount.amount_gross;
        if (gross && parseFloat(gross) > 0) {
          discountLabel = `\u2013${gross}`;
        }
      }
    }

    return {
      productId: String(it.product.id),
      productName: it.product.name,
      productUrl: `/products/${it.product.id}`,
      shortDescription: "",
      unitPrice,
      quantity: it.quantity,
      imageUrl: "",
      originalUnitPrice: hasDiscount ? pricing!.undiscounted!.gross : undefined,
      discountLabel,
    };
  });

  // Phase 2: use backend-computed totals when present.
  if (dto.totals) {
    const t = dto.totals;
    const totalDiscountNum = Number(t.total_discount) || 0;

    return {
      id: String(dto.id),
      currency: t.currency || "USD",
      items,
      // Discount line: shown only when there is an actual reduction.
      discount: totalDiscountNum > 0 ? { amount: t.total_discount } : undefined,
      // Subtotal = original amount before promotion reductions.
      subtotal: t.subtotal_undiscounted,
      // Tax component (informational — already included in total).
      tax: Number(t.total_tax) > 0 ? t.total_tax : undefined,
      // Total payable = post-discount gross (includes tax).
      total: t.total_gross,
    };
  }

  // Fallback: manual calculation for legacy responses without totals.
  const subtotal = items.reduce(
    (acc, it) =>
      addDecimalStrings(acc, mulDecimalString(it.unitPrice, it.quantity)),
    "0.00",
  );

  return {
    id: String(dto.id),
    currency: "USD",
    items,
    discount: undefined,
    subtotal,
    tax: undefined,
    total: subtotal,
  };
}
