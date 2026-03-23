import { apiFetch } from "@/lib/server-fetch";
import type { BaseOrderDto } from "@/lib/api/orders";

export type GuestOrderDto = BaseOrderDto & {
  /**
   * True when the order's contact email already belongs to a registered account.
   * Used by the guest order page to decide whether to show the "create account"
   * banner or an existing-account prompt.
   */
  email_account_exists: boolean;
};

export async function getGuestOrderServer(
  orderId: string | number,
  token: string,
): Promise<GuestOrderDto> {
  const qs = new URLSearchParams({ token }).toString();
  return apiFetch<GuestOrderDto>(`/api/v1/guest/orders/${orderId}/?${qs}`);
}
