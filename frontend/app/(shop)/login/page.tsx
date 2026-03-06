"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import LoginForm from "@/components/auth/LoginForm";
import { login } from "@/lib/api/auth";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();
  const { count: guestCartCount, refreshCart } = useCart();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(
    undefined,
  );

  useEffect(() => {
    if (searchParams.get("verified") === "1") {
      toast.success("Email verified! Please log in to continue.");
    }
  }, [searchParams]);

  // Show a one-time toast when the user is redirected here after a successful
  // email change (ADR-035). The guard prevents duplicate toasts on re-renders.
  const emailChangedToastShown = useRef(false);
  useEffect(() => {
    if (
      searchParams.get("emailChanged") === "1" &&
      !emailChangedToastShown.current
    ) {
      emailChangedToastShown.current = true;
      toast.success("Email changed. Please log in again with your new email.");
    }
  }, [searchParams]);

  // Show a one-time toast when the user is redirected here after a successful
  // password change. The guard prevents duplicate toasts on re-renders.
  const passwordChangedToastShown = useRef(false);
  useEffect(() => {
    if (
      searchParams.get("passwordChanged") === "1" &&
      !passwordChangedToastShown.current
    ) {
      passwordChangedToastShown.current = true;
      toast.success("Password changed. Please log in again.");
    }
  }, [searchParams]);

  // Show a one-time toast when the user is redirected here after a successful
  // password reset. The guard prevents duplicate toasts on re-renders.
  const passwordResetToastShown = useRef(false);
  useEffect(() => {
    if (
      searchParams.get("passwordReset") === "1" &&
      !passwordResetToastShown.current
    ) {
      passwordResetToastShown.current = true;
      toast.success("Password reset. Please log in with your new password.");
    }
  }, [searchParams]);

  const onSubmit = async (values: {
    email: string;
    password: string;
    remember_me: boolean;
  }) => {
    setIsSubmitting(true);
    setErrorMessage(undefined);

    try {
      // Capture guest cart state BEFORE login — cart_token is httpOnly so
      // document.cookie can't read it; we use the CartProvider count instead
      // (hydrated from SSR layout fetch, reflects the current guest cart).
      const hadGuestCart = guestCartCount > 0;

      const resp = await login(values);
      await refresh(); // updates AuthProvider context — HeaderAuthClient reacts instantly
      await refreshCart(); // backend merged guest cart → re-fetch to update badge

      // Preferred: use structured merge report if available
      if (resp?.cart_merge?.performed) {
        toast.success("Your guest cart was merged into your account.");
      } else if (
        hadGuestCart &&
        !searchParams.get("passwordChanged") &&
        !searchParams.get("emailChanged")
      ) {
        // Fallback toast when backend does not yet return a merge report.
        // Suppressed for post-auth redirects (passwordChanged / emailChanged)
        // because CartProvider still holds the stale account-cart count at
        // that point — it is NOT a genuine guest cart.
        toast.success("Your guest cart was merged into your account.");
      }

      if ((resp.claimed_orders ?? 0) > 0) {
        toast.success(
          `Found ${resp.claimed_orders} guest order(s) and linked them to your account.`,
        );
      }

      // MVP redirect: back to products (later you can redirect to /orders)
      router.push("/products");
    } catch (e: any) {
      // backend might return {code,message} or DRF-like detail – keep robust
      const code = e?.response?.data?.code;
      const msg =
        e?.response?.data?.message ||
        e?.response?.data?.detail ||
        e?.message ||
        "Login failed";

      // Known backend issue (Sprint 11 finding): merge conflicts should not block login.
      // Until backend fix is implemented, show an actionable message.
      if (code === "CART_MERGE_STOCK_CONFLICT") {
        setErrorMessage(
          "Login failed because your guest cart could not be merged due to insufficient stock. " +
            "Please adjust your cart items and try again.",
        );
      } else {
        setErrorMessage(String(msg));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md py-10">
      <LoginForm
        onSubmit={onSubmit}
        isSubmitting={isSubmitting}
        errorMessage={errorMessage}
        onGoToRegister={() => router.push("/register")}
        onForgotPassword={() => router.push("/auth/forgot-password")}
      />
    </div>
  );
}
