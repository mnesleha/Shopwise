import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/server-fetch";
import ProfilePageClient from "@/components/profile/ProfilePageClient";
import type { ProfileDto, AddressDto, AccountDto } from "@/lib/api/profile";
import type { MeResponse } from "@/lib/api/auth";

type ProfilePageSearchParams = {
  tab?: string;
  emailChange?: string;
};

type Props = {
  searchParams: Promise<ProfilePageSearchParams>;
};

export default async function ProfilePage({ searchParams }: Props) {
  const params = await searchParams;

  // Auth guard — same pattern as /orders
  let me: MeResponse | null = null;
  try {
    me = await apiFetch<MeResponse>("/api/v1/auth/me/", {
      forwardCookies: true,
    });
  } catch {
    // network error → treat as unauthenticated
  }

  if (!me?.is_authenticated) {
    redirect("/login");
  }

  const initialTab =
    params.tab === "addresses" || params.tab === "account"
      ? params.tab
      : "account";

  // Fetch account, profile and addresses in parallel
  const [account, profile, addresses] = await Promise.all([
    apiFetch<AccountDto>("/api/v1/account/", { forwardCookies: true }),
    apiFetch<ProfileDto>("/api/v1/profile/", { forwardCookies: true }),
    apiFetch<AddressDto[]>("/api/v1/addresses/", { forwardCookies: true }),
  ]);

  return (
    <ProfilePageClient
      account={
        account ?? { email: me?.email ?? "", first_name: "", last_name: "" }
      }
      emailVerified={me?.email_verified ?? false}
      profile={profile}
      addresses={addresses}
      initialTab={initialTab}
      showEmailChangeCancelledToast={params.emailChange === "cancelled"}
    />
  );
}
