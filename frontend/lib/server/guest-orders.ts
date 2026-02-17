import { apiFetch } from "@/lib/server-fetch";

export type GuestOrderDto = {
  id: number;
  status: string;
  items: Array<{
    id: number;
    product: number;
    quantity: number;
    unit_price: string;
    line_total: string;
    discount: null | { type: "FIXED" | "PERCENT"; value: string };
  }>;
  total: string;
};

export async function getGuestOrderServer(orderId: string | number, token: string): Promise<GuestOrderDto> {
  const qs = new URLSearchParams({ token }).toString();
  return apiFetch<GuestOrderDto>(`/api/v1/guest/orders/${orderId}/?${qs}`);
}
