/**
 * /auth/forgot-password — password reset request page.
 *
 * Uses uncontrolled inputs (FormData on submit) per ADR-034.
 * The POST always returns 204 (anti-enumeration): the same toast is shown
 * regardless of whether the email is registered.
 */

"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Mail } from "lucide-react";

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
import { requestPasswordReset } from "@/lib/api/auth";

export default function ForgotPasswordPage() {
  const [busy, setBusy] = React.useState(false);
  // Track whether the form was submitted successfully to show a confirmation
  // state instead of recycling the form.
  const [submitted, setSubmitted] = React.useState(false);

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    // Collect via FormData — uncontrolled inputs, no hydration risk (ADR-034).
    const formData = new FormData(e.currentTarget);
    const email = (formData.get("email") as string).trim().toLowerCase();

    setBusy(true);
    try {
      await requestPasswordReset(email);
      // Anti-enumeration: show the same message regardless of whether the
      // email is registered.
      toast.success("If that email exists, we sent a reset link.");
      setSubmitted(true);
    } catch {
      // Network / server error — still show a generic message so we don't
      // reveal information about the backend state.
      toast.error("Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-md py-10">
      <Card>
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Mail className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">Forgot password?</CardTitle>
          <CardDescription>
            Enter your email and we&apos;ll send you a reset link.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {submitted ? (
            // Confirmation state — no further action needed from the user.
            <div className="space-y-4 text-center">
              <p className="text-sm text-muted-foreground">
                If an account exists for that email, a password reset link has
                been sent. Check your inbox (and spam folder).
              </p>
              <Link
                href="/login"
                className="text-sm font-medium text-primary hover:underline"
              >
                Back to login
              </Link>
            </div>
          ) : (
            <form
              key="forgot-password-form"
              onSubmit={onSubmit}
              className="space-y-4"
              data-testid="forgot-password-form"
            >
              <div className="space-y-2">
                <Label htmlFor="fp_email">Email address</Label>
                <Input
                  id="fp_email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  defaultValue=""
                  placeholder="you@example.com"
                  data-testid="input-fp-email"
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={busy}
                data-testid="submit-fp-btn"
              >
                {busy ? "Sending…" : "Send reset link"}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                <Link
                  href="/login"
                  className="font-medium text-primary hover:underline"
                >
                  Back to login
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
