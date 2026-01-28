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

export async function addCartItem(input: { productId: number; quantity: number }): Promise<void> {
  await api.post("/cart/items/", { product_id: input.productId, quantity: input.quantity });
}

export async function updateCartItemQuantity(input: { productId: number; quantity: number }): Promise<void> {
  // NOTE: path uses productId
  await api.put(`/cart/items/${input.productId}/`, { quantity: input.quantity });
}

export async function deleteCartItem(input: { productId: number }): Promise<void> {
  // NOTE: path uses productId
  await api.delete(`/cart/items/${input.productId}/`);
}
