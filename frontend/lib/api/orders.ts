import { api } from "@/lib/api";

export type BaseOrderDto = {
  id: number;
  status: string;
  items: Array<{
    id: number;
    product: number;
    quantity: number;
    unit_price: string;
    line_total: string;
    discount: null | {
      type: "FIXED" | "PERCENT";
      value: string;
    };
  }>;
  total: string;
};

export type OrderDto = BaseOrderDto
export type GuestOrderDto = BaseOrderDto

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
