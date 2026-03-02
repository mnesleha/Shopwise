import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/server-fetch";
import ProfilePageClient from "@/components/profile/ProfilePageClient";
import type { ProfileDto, AddressDto } from "@/lib/api/profile";

export default async function ProfilePage() {
  // Auth guard — same pattern as /orders
  let isAuthenticated = false;
  try {
    const me = await apiFetch<{ is_authenticated: boolean }>(
      "/api/v1/auth/me/",
      { forwardCookies: true },
    );
    isAuthenticated = Boolean(me?.is_authenticated);
  } catch {
    // network error → treat as unauthenticated
  }

  if (!isAuthenticated) {
    redirect("/login");
  }

  // Fetch profile and addresses in parallel
  const [profile, addresses] = await Promise.all([
    apiFetch<ProfileDto>("/api/v1/profile/", { forwardCookies: true }),
    apiFetch<AddressDto[]>("/api/v1/addresses/", { forwardCookies: true }),
  ]);

  return <ProfilePageClient profile={profile} addresses={addresses} />;
}
