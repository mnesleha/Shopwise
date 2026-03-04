"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import type { AccountDto, AddressDto, ProfileDto } from "@/lib/api/profile";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AccountTab } from "./AccountTab";
import { DefaultAddressesCard } from "./DefaultAddressesCard";
import { AddressesCard } from "./AddressesCard";

type Props = {
  account: AccountDto;
  emailVerified: boolean;
  profile: ProfileDto | null;
  addresses: AddressDto[] | null;
};

/**
 * Client wrapper for the /profile page.
 * Receives SSR-fetched data as props; child components drive mutations
 * and call router.refresh() to reload server data after each change.
 */
export default function ProfilePageClient({
  account,
  emailVerified,
  profile,
  addresses,
}: Props) {
  const safeProfile: ProfileDto = profile ?? {
    id: 0,
    default_shipping_address: null,
    default_billing_address: null,
  };
  const safeAddresses: AddressDto[] = addresses ?? [];

  // Show a one-time toast when the user is redirected here after cancelling
  // an email change via the security notification link (ADR-035).
  const searchParams = useSearchParams();

  const VALID_TABS = ["account", "addresses"] as const;
  type Tab = (typeof VALID_TABS)[number];
  const rawTab = searchParams.get("tab");
  const initialTab: Tab = VALID_TABS.includes(rawTab as Tab)
    ? (rawTab as Tab)
    : "account";

  const [activeTab, setActiveTab] = React.useState<Tab>(initialTab);

  const handleTabChange = (value: string) => {
    const tab = value as Tab;
    setActiveTab(tab);
    // Update URL without triggering a Next.js navigation (no server round-trip).
    const params = new URLSearchParams(window.location.search);
    if (tab === "account") {
      params.delete("tab");
    } else {
      params.set("tab", tab);
    }
    const qs = params.toString();
    window.history.replaceState(
      null,
      "",
      qs ? `?${qs}` : window.location.pathname,
    );
  };

  const cancelToastShown = React.useRef(false);
  React.useEffect(() => {
    if (
      searchParams.get("emailChange") === "cancelled" &&
      !cancelToastShown.current
    ) {
      cancelToastShown.current = true;
      toast.info("Email change cancelled successfully.");
    }
  }, [searchParams]);

  return (
    <div
      className="mx-auto w-full max-w-2xl space-y-6"
      data-testid="profile-page"
    >
      <h1 className="text-2xl font-semibold">My Profile</h1>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="mb-4">
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="addresses">Addresses</TabsTrigger>
        </TabsList>

        <TabsContent value="account">
          <AccountTab account={account} emailVerified={emailVerified} />
        </TabsContent>

        <TabsContent value="addresses">
          <div className="space-y-6">
            <DefaultAddressesCard
              profile={safeProfile}
              addresses={safeAddresses}
            />
            <AddressesCard addresses={safeAddresses} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
