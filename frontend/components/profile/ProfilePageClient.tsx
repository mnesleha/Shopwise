"use client";

import type { AddressDto, ProfileDto } from "@/lib/api/profile";
import { DefaultAddressesCard } from "./DefaultAddressesCard";
import { AddressesCard } from "./AddressesCard";

type Props = {
  profile: ProfileDto;
  addresses: AddressDto[];
};

/**
 * Client wrapper for the /profile page.
 * Receives SSR-fetched data as props; child components drive mutations
 * and call router.refresh() to reload server data after each change.
 */
export default function ProfilePageClient({ profile, addresses }: Props) {
  return (
    <div
      className="mx-auto w-full max-w-2xl space-y-6"
      data-testid="profile-page"
    >
      <h1 className="text-2xl font-semibold">My Profile</h1>

      <DefaultAddressesCard profile={profile} addresses={addresses} />
      <AddressesCard addresses={addresses} />
    </div>
  );
}
