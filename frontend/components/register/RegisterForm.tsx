"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, Eye, EyeOff, UserPlus, AlertCircle } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth/AuthProvider";
import { register } from "@/lib/api/auth";
import { useCart } from "@/components/cart/CartProvider";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";

// ------------------------------------------------------------------ Types

interface FieldErrors {
  email?: string;
  password?: string;
}

interface RegisterResponse {
  is_authenticated: boolean;
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  email_verified: boolean;
}

// Simple email regex (same as LoginForm)
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Backend currently accepts short passwords in dev/test flows (e.g. "customer_6").
// Keep FE validation aligned to avoid blocking E2E guard scenarios.
const MIN_PASSWORD_LENGTH = 1;

// ------------------------------------------------------------------ Component

export default function RegisterForm() {
  const router = useRouter();
  const { refresh } = useAuth();
  const { refreshCart } = useCart();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [errors, setErrors] = React.useState<FieldErrors>({});
  const [serverError, setServerError] = React.useState<string | undefined>();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const emailRef = React.useRef<HTMLInputElement>(null);
  const passwordRef = React.useRef<HTMLInputElement>(null);

  // ---- Validation (on submit only) ----
  function validate(): FieldErrors {
    const errs: FieldErrors = {};

    if (!email.trim()) {
      errs.email = "Email is required.";
    } else if (!EMAIL_RE.test(email.trim())) {
      errs.email = "Please enter a valid email address.";
    }

    if (!password) {
      errs.password = "Password is required.";
    } else if (password.length < MIN_PASSWORD_LENGTH) {
      errs.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    }

    return errs;
  }

  function focusFirstError(errs: FieldErrors) {
    if (errs.email) {
      emailRef.current?.focus();
    } else if (errs.password) {
      passwordRef.current?.focus();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(undefined);

    const errs = validate();
    setErrors(errs);

    if (Object.keys(errs).length > 0) {
      focusFirstError(errs);
      return;
    }

    setIsSubmitting(true);

    try {
      const data = (await register({
        email: email.trim(),
        password,
      })) as RegisterResponse;

      // /auth/register/ now sets auth cookies directly — no second login() needed.
      await refresh();
      await refreshCart();

      toast.success("Account created and signed in.");

      if (!data.email_verified) {
        toast.info(
          "Verify your email to access order history. You can resend verification email from the Orders page.",
        );
      }

      router.replace("/products");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Registration failed.";
      setServerError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <Card className="w-full max-w-md">
        {/* ---- Header ---- */}
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <UserPlus className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">Create account</CardTitle>
          <CardDescription>Sign up to start placing orders</CardDescription>
        </CardHeader>

        <CardContent>
          {/* ---- Server / global error ---- */}
          {serverError && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}

          <form
            onSubmit={handleSubmit}
            noValidate
            className="flex flex-col gap-5"
          >
            {/* ---- Email ---- */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="register-email">Email</Label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  ref={emailRef}
                  id="register-email"
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email)
                      setErrors((prev) => ({ ...prev, email: undefined }));
                  }}
                  className={cn(
                    "pl-10",
                    errors.email &&
                      "border-destructive focus-visible:ring-destructive",
                  )}
                  aria-invalid={!!errors.email}
                  aria-describedby={
                    errors.email ? "register-email-error" : undefined
                  }
                />
              </div>
              {errors.email && (
                <p
                  id="register-email-error"
                  className="text-sm text-destructive"
                >
                  {errors.email}
                </p>
              )}
            </div>

            {/* ---- Password ---- */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="register-password">Password</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  ref={passwordRef}
                  id="register-password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Min. 8 characters"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errors.password)
                      setErrors((prev) => ({ ...prev, password: undefined }));
                  }}
                  className={cn(
                    "pl-10 pr-10",
                    errors.password &&
                      "border-destructive focus-visible:ring-destructive",
                  )}
                  aria-invalid={!!errors.password}
                  aria-describedby={
                    errors.password ? "register-password-error" : undefined
                  }
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p
                  id="register-password-error"
                  className="text-sm text-destructive"
                >
                  {errors.password}
                </p>
              )}
            </div>

            {/* ---- Submit ---- */}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Creating\u2026" : "Create account"}
            </Button>
          </form>
        </CardContent>

        {/* ---- Footer ---- */}
        <Separator />
        <CardFooter className="justify-center pt-6">
          <p className="text-sm text-muted-foreground">
            {"Already have an account? "}
            <Link
              href="/login"
              className="font-medium text-primary hover:underline"
            >
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
