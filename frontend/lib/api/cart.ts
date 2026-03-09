import { api } from "@/lib/api";

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
  }>;
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
