import type { PublicTrackingDto } from "@/lib/api/tracking";
import { apiFetch } from "@/lib/server-fetch";

export async function getPublicTrackingServer(
  trackingNumber: string,
): Promise<PublicTrackingDto> {
  return apiFetch<PublicTrackingDto>(
    `/api/v1/tracking/${encodeURIComponent(trackingNumber)}/`,
  );
}
