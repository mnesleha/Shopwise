import { apiFetch } from "@/lib/server-fetch";
import type { OrderDto } from "@/lib/api/orders";

export async function getOrderServer(orderId: string | number): Promise<OrderDto> {
  return apiFetch<OrderDto>(`/api/v1/orders/${orderId}/`);
}
