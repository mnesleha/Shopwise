"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { patchAccount } from "@/lib/api/profile";
import type { AccountDto } from "@/lib/api/profile";
import ResendVerificationButton from "@/components/auth/ResendVerificationButton";
import { useAuth } from "@/components/auth/AuthProvider";

type Props = {
  account: AccountDto;
  emailVerified: boolean;
};

export function AccountTab({ account, emailVerified }: Props) {
  const router = useRouter();
  const { refresh: refreshAuth } = useAuth();

  const [firstName, setFirstName] = React.useState(account.first_name);
  const [lastName, setLastName] = React.useState(account.last_name);
  const [saving, setSaving] = React.useState(false);

  // Keep local state in sync when server data changes (e.g. after router.refresh)
  React.useEffect(() => {
    setFirstName(account.first_name);
    setLastName(account.last_name);
  }, [account.first_name, account.last_name]);

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await patchAccount({ first_name: firstName, last_name: lastName });
      toast.success("Profile updated.");
      // Refresh AuthProvider so the header reflects the new name immediately,
      // then revalidate server components (RSC cache).
      await refreshAuth();
      router.refresh();
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Failed to save changes.";
      toast.error(String(msg));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Display name */}
      <Card>
        <CardHeader>
          <CardTitle>Display name</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSave} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="first-name">First name</Label>
                <Input
                  id="first-name"
                  data-testid="input-first-name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  autoComplete="given-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last-name">Last name</Label>
                <Input
                  id="last-name"
                  data-testid="input-last-name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  autoComplete="family-name"
                />
              </div>
            </div>
            <Button
              type="submit"
              disabled={saving}
              data-testid="save-account-btn"
            >
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Login email + verification status */}
      <Card>
        <CardHeader>
          <CardTitle>Email address</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label>Login email</Label>
            <p
              className="text-sm font-medium"
              data-testid="account-email"
            >
              {account.email}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Status:</span>
            {emailVerified ? (
              <Badge
                variant="default"
                className="bg-green-600 hover:bg-green-600"
                data-testid="badge-verified"
              >
                Verified
              </Badge>
            ) : (
              <Badge variant="destructive" data-testid="badge-unverified">
                Not verified
              </Badge>
            )}
          </div>

          {!emailVerified && (
            <ResendVerificationButton email={account.email} />
          )}

          {/* Change email — placeholder; not yet implemented */}
          <div className="pt-2 border-t space-y-1">
            <p className="text-sm font-medium">Change email</p>
            <p className="text-xs text-muted-foreground">Coming soon.</p>
          </div>
        </CardContent>
      </Card>

      {/* Change password — placeholder; not yet implemented */}
      <Card>
        <CardHeader>
          <CardTitle>Password</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <p className="text-sm font-medium">Change password</p>
          <p className="text-xs text-muted-foreground">Coming soon.</p>
        </CardContent>
      </Card>
    </div>
  );
}
