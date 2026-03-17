import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Phase 2 pricing types (Slice 4 — cart pricing integration)
// ---------------------------------------------------------------------------

/** A single pricing tier (undiscounted or discounted) for one cart item unit. */
export type CartItemPricingTierDto = {
  net: string;
  gross: string;
  tax: string;
  currency: string;
  tax_rate: string;
};

/** Per-unit pricing breakdown for a cart item — same shape as the catalogue API. */
export type CartItemPricingDto = {
  undiscounted: CartItemPricingTierDto;
  discounted: CartItemPricingTierDto;
  discount: {
    amount_net: string;
    amount_gross: string;
    percentage: string | null;
    promotion_code: string | null;
    promotion_type: string | null;
  };
};

/** Backend-computed aggregate pricing totals for the whole cart. */
export type CartTotalsDto = {
  /** sum(undiscounted_gross × qty) — original total before promotions. */
  subtotal_undiscounted: string;
  /** sum(discounted_gross × qty) — total after promotions; equals total_gross. */
  subtotal_discounted: string;
  /** subtotal_undiscounted − subtotal_discounted (≥ 0). */
  total_discount: string;
  /** sum(discounted_tax × qty). */
  total_tax: string;
  /** Total amount payable (= subtotal_discounted). */
  total_gross: string;
  currency: string;
  item_count: number;
  // Phase 4 / Slice 3: order-level AUTO_APPLY promotion
  /** True when an order-level promotion is automatically applied. */
  order_discount_applied: boolean;
  /** Gross reduction from the order-level promotion, or null when none. */
  order_discount_amount: string | null;
  /** Code of the applied order promotion, or null. */
  order_discount_promotion_code: string | null;
  /** Name of the applied order promotion, or null. */
  order_discount_promotion_name: string | null;
  /** Total gross payable after order-level discount, or null when none. */
  total_gross_after_order_discount: string | null;
  /** Total VAT after order-level discount reallocation, or null when none. */
  total_tax_after_order_discount: string | null;
  // Phase 4 / Slice 4: threshold reward progress
  /** Progress towards a threshold-based order reward, or null when none exists. */
  threshold_reward?: {
    is_unlocked: boolean;
    promotion_name: string;
    threshold: string;
    current_basis: string;
    remaining: string;
    currency: string;
  } | null;
  // Phase 4 / Slice 5C: order discount decision engine
  /**
   * Campaign offer outcome:
   * - "APPLIED"    — the claimed offer is the current winner.
   * - "SUPERSEDED" — a better auto-apply promotion is already active.
   * - null          — no campaign offer context.
   */
  campaign_outcome?: string | null;
  /**
   * Next meaningful order-level winner transition, or null when no better
   * promotion exists at a higher cart value.
   */
  order_discount_next_upgrade?: {
    /** Cart gross total at which the better promotion becomes the winner. */
    threshold: string;
    /** Additional spend required to reach the threshold. */
    remaining: string;
    /** Human-readable name of the next winning promotion. */
    promotion_name: string;
    /** ISO 4217 currency code. */
    currency: string;
  } | null;
};

export type CartDto = {
  id: number;
  status: string;
  items: Array<{
    id: number; // cart item id (exists, but NOT used for update/delete)
    product: {
      id: number; // product id (THIS is used for update/delete)
      name: string;
      price: string;
    };
    quantity: number;
    price_at_add_time: string;
    /** Phase 2: structured unit pricing. null for unmigrated products. */
    pricing?: CartItemPricingDto | null;
  }>;
  /** Phase 2: backend-computed cart-level pricing totals. */
  totals?: CartTotalsDto;
};

export async function getCart(): Promise<CartDto> {
  const res = await api.get<CartDto>("/cart/");
  return res.data;
}

export async function addCartItem(input: {
  productId: number;
  quantity: number;
}): Promise<void> {
  await api.post("/cart/items/", {
    product_id: input.productId,
    quantity: input.quantity,
  });
}

export async function updateCartItemQuantity(input: {
  productId: number;
  quantity: number;
}): Promise<void> {
  // NOTE: path uses productId; PATCH = partial update (quantity only)
  await api.patch(`/cart/items/${input.productId}/`, {
    quantity: input.quantity,
  });
}

export async function deleteCartItem(input: {
  productId: number;
}): Promise<void> {
  // NOTE: path uses productId
  await api.delete(`/cart/items/${input.productId}/`);
}

/**
 * DELETE /cart/
 *
 * Removes all items from the active cart in a single request.
 * The Cart row itself is preserved; the cart remains an empty active cart.
 * Idempotent: always resolves, even when the cart is already empty.
 */
export async function clearCart(): Promise<void> {
  await api.delete("/cart/");
}

// ── Cart merge ────────────────────────────────────────────────────────────────

export type CartMergeWarning = {
  code: string;
  product_id: number;
  requested: number;
  applied: number;
};

export type CartMergeReport = {
  performed: boolean;
  result: "NOOP" | "ADOPTED" | "MERGED";
  items_added: number;
  items_updated: number;
  items_removed: number;
  warnings: CartMergeWarning[];
};

/**
 * POST /cart/merge/
 *
 * Merges the current guest cart (identified by the httpOnly cart_token cookie)
 * into the authenticated user's cart.  Always returns 200 with a CartMergeReport.
 * Requires authentication.
 */
export async function mergeCart(): Promise<CartMergeReport> {
  const res = await api.post<CartMergeReport>("/cart/merge/");
  return res.data;
}

// ---------------------------------------------------------------------------
// Phase 4 / Slice 5B: campaign offer claim
// ---------------------------------------------------------------------------

export type ClaimOfferResponse = {
  /** Human-readable name of the applied promotion. */
  promotion_name: string;
  /** Internal code of the applied promotion. */
  promotion_code: string;
};

/**
 * POST /cart/offer/claim/
 *
 * Validates the given offer token and binds it to the current session.
 * Subsequent ``GET /cart/`` calls will reflect the campaign discount.
 *
 * Throws on 400 (inactive/non-claimable offer) or 404 (offer not found).
 */
export async function claimCampaignOffer(
  token: string,
): Promise<ClaimOfferResponse> {
  const res = await api.post<ClaimOfferResponse>("/cart/offer/claim/", {
    token,
  });
  return res.data;
}
