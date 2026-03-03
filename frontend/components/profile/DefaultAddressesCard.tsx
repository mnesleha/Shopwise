"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { updateProfile } from "@/lib/api/profile";
import type { AddressDto, ProfileDto } from "@/lib/api/profile";

type Props = {
  profile: ProfileDto;
  addresses: AddressDto[];
};

export function DefaultAddressesCard({ profile, addresses }: Props) {
  const router = useRouter();

  const [shippingId, setShippingId] = React.useState<string>(
    profile.default_shipping_address?.toString() ?? "",
  );
  const [billingId, setBillingId] = React.useState<string>(
    profile.default_billing_address?.toString() ?? "",
  );

  // Sync local state when the server-side profile prop changes (e.g. after
  // router.refresh() triggered by address deletion cascading a SET_NULL).
  React.useEffect(() => {
    setShippingId(profile.default_shipping_address?.toString() ?? "");
  }, [profile.default_shipping_address]);

  React.useEffect(() => {
    setBillingId(profile.default_billing_address?.toString() ?? "");
  }, [profile.default_billing_address]);

  const onShippingChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    const prev = shippingId;
    setShippingId(val); // optimistic
    try {
      await updateProfile({
        default_shipping_address: val ? Number(val) : null,
      });
      toast.success("Default address updated.");
      router.refresh();
    } catch {
      setShippingId(prev); // revert optimistic update on failure
      toast.error("Failed to update default address.");
    }
  };

  const onBillingChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    const prev = billingId;
    setBillingId(val); // optimistic
    try {
      await updateProfile({
        default_billing_address: val ? Number(val) : null,
      });
      toast.success("Default address updated.");
      router.refresh();
    } catch {
      setBillingId(prev); // revert optimistic update on failure
      toast.error("Failed to update default address.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Default Addresses</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="default-shipping">Default shipping address</Label>
          <select
            id="default-shipping"
            data-testid="select-default-shipping"
            value={shippingId}
            onChange={onShippingChange}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">— none —</option>
            {addresses.map((a) => (
              <option key={a.id} value={a.id.toString()}>
                {a.full_name} – {a.street_line_1}, {a.city}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="default-billing">Default billing address</Label>
          <select
            id="default-billing"
            data-testid="select-default-billing"
            value={billingId}
            onChange={onBillingChange}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">— none —</option>
            {addresses.map((a) => (
              <option key={a.id} value={a.id.toString()}>
                {a.full_name} – {a.street_line_1}, {a.city}
              </option>
            ))}
          </select>
        </div>
      </CardContent>
    </Card>
  );
}
