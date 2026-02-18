import { getAccessToken } from "@/lib/auth/tokens";

export function hasAccessToken(): boolean {
  return Boolean(getAccessToken());
}
