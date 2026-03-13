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
  /** Line-level promotions discount summary. */
  discount?: {
    code?: string;
    description?: string;
    amount?: string;
  };
  /**
   * Phase 4 / Slice 3: order-level AUTO_APPLY promotion discount.
   * Present when the backend resolved an eligible order promotion.
   */
  orderDiscount?: {
    /** Human-readable promotion name, e.g. "Spring order discount". */
    promotionName: string;
    /** Gross discount amount as a decimal string. */
    amount: string;
    /** Cart total gross after this discount as a decimal string. */
    totalGrossAfter: string;
    /** Cart total VAT after this discount as a decimal string. */
    totalTaxAfter: string;
  };
  /**
   * Phase 4 / Slice 4: progress towards a threshold-based order reward.
   * Undefined when no threshold promotion exists for this cart.
   */
  thresholdReward?: {
    /** True when the threshold has been met and the reward is applied. */
    isUnlocked: boolean;
    /** Human-readable promotion name, e.g. "Free shipping over €100". */
    promotionName: string;
    /** Required gross total to unlock the reward, as a decimal string. */
    threshold: string;
    /** Current cart gross (basis for threshold evaluation), as a decimal string. */
    currentBasis: string;
    /** Amount still needed to reach the threshold, "0.00" when unlocked. */
    remaining: string;
    /** Currency code, e.g. "EUR". */
    currency: string;
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

    // Phase 4 / Slice 3: map order-level discount when the backend applied one.
    let orderDiscount: CartVm["orderDiscount"];

    // Phase 4 / Slice 4: map threshold reward progress.
    let thresholdReward: CartVm["thresholdReward"];
    if (t.threshold_reward) {
      const tr = t.threshold_reward;
      thresholdReward = {
        isUnlocked: tr.is_unlocked,
        promotionName: tr.promotion_name,
        threshold: tr.threshold,
        currentBasis: tr.current_basis,
        remaining: tr.remaining,
        currency: tr.currency,
      };
    }
    if (
      t.order_discount_applied &&
      t.order_discount_amount !== null &&
      t.order_discount_promotion_name !== null &&
      t.total_gross_after_order_discount !== null &&
      t.total_tax_after_order_discount !== null
    ) {
      orderDiscount = {
        promotionName: t.order_discount_promotion_name!,
        amount: t.order_discount_amount!,
        totalGrossAfter: t.total_gross_after_order_discount!,
        totalTaxAfter: t.total_tax_after_order_discount!,
      };
    }

    // The displayed total is the post-order-discount figure when one is applied.
    const total = orderDiscount ? orderDiscount.totalGrossAfter : t.total_gross;

    // Tax displayed is also the post-order-discount figure when one is applied.
    const tax = orderDiscount
      ? Number(orderDiscount.totalTaxAfter) > 0
        ? orderDiscount.totalTaxAfter
        : undefined
      : Number(t.total_tax) > 0
        ? t.total_tax
        : undefined;

    return {
      id: String(dto.id),
      currency: t.currency || "USD",
      items,
      // Discount line: shown only when there is an actual reduction.
      discount: totalDiscountNum > 0 ? { amount: t.total_discount } : undefined,
      orderDiscount,
      thresholdReward,
      // Subtotal = original amount before promotion reductions.
      subtotal: t.subtotal_undiscounted,
      // Tax component (informational — already included in total).
      tax,
      // Total payable = post-discount gross (includes tax).
      total,
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
