"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import LoginForm from "@/components/auth/LoginForm";
import { login } from "@/lib/api/auth";
import { mergeCart } from "@/lib/api/cart";
import { claimOrders } from "@/lib/api/orders";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();
  const { refreshCart } = useCart();
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
      await login(values);
      await refresh(); // updates AuthProvider context — HeaderAuthClient reacts instantly

      // ── Cart merge ──────────────────────────────────────────────────────────
      // The backend reads the httpOnly cart_token cookie automatically.
      const mergeReport = await mergeCart();
      if (mergeReport.performed && mergeReport.result !== "NOOP") {
        const mergeMsg =
          mergeReport.result === "ADOPTED"
            ? "We restored your saved cart."
            : "We synced your carts.";
        toast.success(mergeMsg);
      }
      if (mergeReport.warnings.length > 0) {
        // Persist warnings once so the cart page can highlight affected items.
        sessionStorage.setItem(
          "cartMergeWarnings",
          JSON.stringify(mergeReport.warnings),
        );
        // Show sticky warning toast with a direct link to the cart page.
        // Using a `let` variable so the onClick closure can dismiss by id.
        let toastId: string | number;
        toastId = toast.warning(
          "Some item quantities were adjusted due to stock availability.",
          {
            duration: Infinity,
            action: {
              label: "Review adjustments",
              onClick: () => {
                router.push("/cart?stockAdjusted=1");
                toast.dismiss(toastId);
              },
            },
          },
        );
      }

      await refreshCart(); // re-fetch to update the cart badge

      // ── Orders claim ────────────────────────────────────────────────────────
      const claimReport = await claimOrders();
      if (claimReport.claimed_orders > 0) {
        toast.success(
          `We found ${claimReport.claimed_orders} guest order(s) and linked them to your account.`,
        );
      }

      // MVP redirect: back to products
      router.push("/products");
    } catch (e: any) {
      // backend might return {code,message} or DRF-like detail – keep robust
      const msg =
        e?.response?.data?.message ||
        e?.response?.data?.detail ||
        e?.message ||
        "Login failed";
      setErrorMessage(String(msg));
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
