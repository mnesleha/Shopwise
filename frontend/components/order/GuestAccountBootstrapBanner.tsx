"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Lock, Eye, EyeOff, UserPlus, AlertCircle, LogIn } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/auth/AuthProvider";
import { bootstrapGuestAccount } from "@/lib/api/auth";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// ── Test IDs ─────────────────────────────────────────────────────────────────
export const GUEST_BOOTSTRAP_BANNER = "guest-bootstrap-banner";
export const GUEST_BOOTSTRAP_EXISTING_ACCOUNT =
  "guest-bootstrap-existing-account";
export const GUEST_BOOTSTRAP_FORM = "guest-bootstrap-form";
export const GUEST_BOOTSTRAP_SUBMIT = "guest-bootstrap-submit";

// ── Props ─────────────────────────────────────────────────────────────────────

interface GuestAccountBootstrapBannerProps {
  orderId: number | string;
  token: string;
  emailAccountExists: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

/**
 * Banner shown on the verified guest order page offering account creation or
 * directing the user to sign in if an account already exists.
 *
 * Rendering rules:
 * - Authenticated user → no create-account CTA; show a "Link order" action
 *   that uses the existing claim endpoint.
 * - Unauthenticated + email_account_exists=true → prompt to log in.
 * - Unauthenticated + email_account_exists=false → password form for bootstrap.
 */
export default function GuestAccountBootstrapBanner({
  orderId,
  token,
  emailAccountExists,
}: GuestAccountBootstrapBannerProps) {
  const router = useRouter();
  const { isAuthenticated, refresh } = useAuth();

  const [password, setPassword] = React.useState("");
  const [passwordConfirm, setPasswordConfirm] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = React.useState(false);
  const [fieldErrors, setFieldErrors] = React.useState<{
    password?: string;
    password_confirm?: string;
  }>({});
  const [serverError, setServerError] = React.useState<string | undefined>();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // ── Authenticated user: offer to claim order ───────────────────────────────

  const [isClaiming, setIsClaiming] = React.useState(false);

  async function handleClaim() {
    setIsClaiming(true);
    try {
      const res = await api.post<{ claimed_orders: number }>("/orders/claim/");
      const count = res.data.claimed_orders;
      if (count > 0) {
        toast.success(
          `${count} order${count !== 1 ? "s" : ""} linked to your account.`,
        );
        router.push(`/orders/${orderId}`);
      } else {
        toast.info(
          "No orders to link — this order may already be in your account.",
        );
        router.push(`/orders/${orderId}`);
      }
    } catch {
      toast.error("Failed to link orders. Please try again.");
    } finally {
      setIsClaiming(false);
    }
  }

  if (isAuthenticated) {
    return (
      <Card
        className="mx-auto mb-6 max-w-4xl border-primary/30 bg-primary/5"
        data-testid={GUEST_BOOTSTRAP_BANNER}
      >
        <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">
            You are signed in. Link this order to your account to view it in
            your order history.
          </p>
          <Button
            size="sm"
            variant="outline"
            onClick={handleClaim}
            disabled={isClaiming}
          >
            {isClaiming ? "Linking…" : "Link order to account"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  // ── Existing account: prompt to log in ────────────────────────────────────

  if (emailAccountExists) {
    return (
      <Card
        className="mx-auto mb-6 max-w-4xl"
        data-testid={GUEST_BOOTSTRAP_EXISTING_ACCOUNT}
      >
        <CardContent className="flex flex-col gap-3 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-2">
            <LogIn className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <p className="text-sm text-muted-foreground">
              An account with this email already exists. Log in to view all your
              orders.
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => router.push("/login")}
          >
            Sign in
          </Button>
        </CardContent>
      </Card>
    );
  }

  // ── New account: password-only bootstrap form ──────────────────────────────

  function validate(): typeof fieldErrors {
    const errs: typeof fieldErrors = {};
    if (!password) {
      errs.password = "Password is required.";
    }
    if (!passwordConfirm) {
      errs.password_confirm = "Please confirm your password.";
    } else if (password && password !== passwordConfirm) {
      errs.password_confirm = "Passwords do not match.";
    }
    return errs;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(undefined);

    const errs = validate();
    setFieldErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setIsSubmitting(true);
    try {
      await bootstrapGuestAccount(orderId, token, {
        password,
        password_confirm: passwordConfirm,
      });

      // Bootstrap sets auth cookies; refresh frontend auth state.
      await refresh();

      toast.success("Account created and signed in.");
      router.push(`/orders/${orderId}`);
    } catch (err: unknown) {
      const anyErr = err as {
        response?: { data?: { detail?: string; code?: string } };
      };
      const code = anyErr?.response?.data?.code;
      if (code === "EMAIL_ALREADY_REGISTERED") {
        setServerError(
          "An account with this email already exists. Please log in.",
        );
      } else {
        const detail =
          anyErr?.response?.data?.detail ??
          "Account creation failed. Please try again.";
        setServerError(detail);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card
      className="mx-auto mb-6 max-w-4xl border-primary/30"
      data-testid={GUEST_BOOTSTRAP_BANNER}
    >
      <CardHeader>
        <div className="flex items-center gap-2">
          <UserPlus className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg">
            Save your order to an account
          </CardTitle>
        </div>
        <CardDescription>
          Create a free account to access your order history and speed up future
          checkouts with saved addresses.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {serverError && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}
        <form
          onSubmit={handleSubmit}
          data-testid={GUEST_BOOTSTRAP_FORM}
          className="max-w-md space-y-4"
          noValidate
        >
          {/* Password */}
          <div className="space-y-1">
            <Label htmlFor="bootstrap-password">
              <Lock className="mr-1 inline h-3.5 w-3.5" />
              Password
            </Label>
            <div className="relative">
              <Input
                id="bootstrap-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={fieldErrors.password ? "border-destructive" : ""}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {fieldErrors.password && (
              <p className="text-sm text-destructive">{fieldErrors.password}</p>
            )}
          </div>

          {/* Confirm password */}
          <div className="space-y-1">
            <Label htmlFor="bootstrap-password-confirm">
              <Lock className="mr-1 inline h-3.5 w-3.5" />
              Confirm password
            </Label>
            <div className="relative">
              <Input
                id="bootstrap-password-confirm"
                type={showPasswordConfirm ? "text" : "password"}
                autoComplete="new-password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                className={
                  fieldErrors.password_confirm ? "border-destructive" : ""
                }
              />
              <button
                type="button"
                onClick={() => setShowPasswordConfirm((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                aria-label={
                  showPasswordConfirm ? "Hide password" : "Show password"
                }
              >
                {showPasswordConfirm ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {fieldErrors.password_confirm && (
              <p className="text-sm text-destructive">
                {fieldErrors.password_confirm}
              </p>
            )}
          </div>

          <Button
            type="submit"
            disabled={isSubmitting}
            data-testid={GUEST_BOOTSTRAP_SUBMIT}
          >
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
