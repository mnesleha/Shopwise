/**
 * Client form for /auth/reset-password.
 *
 * Receives the token from the server page wrapper. Handles:
 *  - Missing / empty token → immediate error state
 *  - submit → confirmPasswordReset → redirect to /login?passwordReset=1
 *  - API validation errors (400) → inline field messages
 *  - password show/hide toggles on both fields
 *
 * Uncontrolled inputs with FormData (ADR-034).
 */

"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Eye, EyeOff, KeyRound } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { confirmPasswordReset } from "@/lib/api/auth";

interface FieldErrors {
  token?: string[];
  new_password?: string[];
  new_password_confirm?: string[];
  non_field_errors?: string[];
}

interface Props {
  token: string;
}

export default function ResetPasswordForm({ token }: Props) {
  const router = useRouter();

  const [busy, setBusy] = React.useState(false);
  const [fieldErrors, setFieldErrors] = React.useState<FieldErrors>({});
  const [showPassword, setShowPassword] = React.useState(false);
  const [showConfirm, setShowConfirm] = React.useState(false);

  // Missing or empty token — show an error state immediately without letting
  // the user fill in a form that will definitely fail.
  if (!token) {
    return (
      <div className="mx-auto max-w-md py-10">
        <Card>
          <CardContent className="pt-6 text-center space-y-4">
            <p className="text-sm text-destructive font-medium">
              No reset token found. The link may be missing or incomplete.
            </p>
            <p className="text-sm text-muted-foreground">
              Please request a{" "}
              <Link
                href="/auth/forgot-password"
                className="font-medium text-primary hover:underline"
              >
                new reset link
              </Link>
              .
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFieldErrors({});

    const formData = new FormData(e.currentTarget);
    const new_password = formData.get("new_password") as string;
    const new_password_confirm = formData.get("new_password_confirm") as string;

    // Quick client-side sanity check to avoid a trivially avoidable round trip.
    if (new_password !== new_password_confirm) {
      setFieldErrors({ new_password_confirm: ["Passwords do not match."] });
      return;
    }

    setBusy(true);
    try {
      await confirmPasswordReset({ token, new_password, new_password_confirm });
      router.push("/login?passwordReset=1");
    } catch (err: unknown) {
      if (
        err &&
        typeof err === "object" &&
        "status" in err &&
        (err as { status: number }).status === 400
      ) {
        // Validation error — extract DRF field messages.
        const body = (err as { body?: unknown }).body;
        if (body && typeof body === "object") {
          setFieldErrors(body as FieldErrors);
          return;
        }
      }
      toast.error("Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const firstGlobalError =
    fieldErrors.non_field_errors?.[0] ?? fieldErrors.token?.[0];

  return (
    <div className="mx-auto max-w-md py-10">
      <Card>
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <KeyRound className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">Set new password</CardTitle>
          <CardDescription>
            Choose a strong password for your account.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form
            // forceRemount if token changes (shouldn't normally happen, but safe)
            key={token}
            onSubmit={onSubmit}
            className="space-y-4"
            data-testid="reset-password-form"
          >
            {/* Token / global errors */}
            {firstGlobalError && (
              <p
                className="text-sm text-destructive"
                data-testid="rp-global-error"
              >
                {firstGlobalError}
              </p>
            )}

            {/* New password */}
            <div className="space-y-2">
              <Label htmlFor="rp_new_password">New password</Label>
              <div className="relative">
                <Input
                  id="rp_new_password"
                  name="new_password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  defaultValue=""
                  className="pr-10"
                  aria-invalid={!!fieldErrors.new_password}
                  data-testid="input-rp-new-password"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {fieldErrors.new_password?.map((e) => (
                <p key={e} className="text-xs text-destructive">
                  {e}
                </p>
              ))}
            </div>

            {/* Confirm password */}
            <div className="space-y-2">
              <Label htmlFor="rp_new_password_confirm">Confirm password</Label>
              <div className="relative">
                <Input
                  id="rp_new_password_confirm"
                  name="new_password_confirm"
                  type={showConfirm ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  defaultValue=""
                  className="pr-10"
                  aria-invalid={!!fieldErrors.new_password_confirm}
                  data-testid="input-rp-new-password-confirm"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => setShowConfirm((v) => !v)}
                  aria-label={
                    showConfirm
                      ? "Hide confirm password"
                      : "Show confirm password"
                  }
                >
                  {showConfirm ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {fieldErrors.new_password_confirm?.map((e) => (
                <p key={e} className="text-xs text-destructive">
                  {e}
                </p>
              ))}
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={busy}
              data-testid="submit-rp-btn"
            >
              {busy ? "Saving…" : "Reset password"}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              <Link
                href="/auth/forgot-password"
                className="font-medium text-primary hover:underline"
              >
                Request a new link
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
