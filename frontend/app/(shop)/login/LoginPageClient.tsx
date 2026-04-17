"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import LoginForm from "@/components/auth/LoginForm";
import { login } from "@/lib/api/auth";
import { mergeCart } from "@/lib/api/cart";
import { claimOrders } from "@/lib/api/orders";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";

type LoginPageClientProps = {
  showVerifiedToast: boolean;
  showEmailChangedToast: boolean;
  showPasswordChangedToast: boolean;
  showPasswordResetToast: boolean;
};

export default function LoginPageClient({
  showVerifiedToast,
  showEmailChangedToast,
  showPasswordChangedToast,
  showPasswordResetToast,
}: LoginPageClientProps) {
  const router = useRouter();
  const { refresh } = useAuth();
  const { refreshCart } = useCart();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(
    undefined,
  );

  useEffect(() => {
    if (showVerifiedToast) {
      toast.success("Email verified! Please log in to continue.");
    }
  }, [showVerifiedToast]);

  const emailChangedToastShown = useRef(false);
  useEffect(() => {
    if (showEmailChangedToast && !emailChangedToastShown.current) {
      emailChangedToastShown.current = true;
      toast.success("Email changed. Please log in again with your new email.");
    }
  }, [showEmailChangedToast]);

  const passwordChangedToastShown = useRef(false);
  useEffect(() => {
    if (showPasswordChangedToast && !passwordChangedToastShown.current) {
      passwordChangedToastShown.current = true;
      toast.success("Password changed. Please log in again.");
    }
  }, [showPasswordChangedToast]);

  const passwordResetToastShown = useRef(false);
  useEffect(() => {
    if (showPasswordResetToast && !passwordResetToastShown.current) {
      passwordResetToastShown.current = true;
      toast.success("Password reset. Please log in with your new password.");
    }
  }, [showPasswordResetToast]);

  const onSubmit = async (values: {
    email: string;
    password: string;
    remember_me: boolean;
  }) => {
    setIsSubmitting(true);
    setErrorMessage(undefined);

    try {
      await login(values);
      await refresh();

      const mergeReport = await mergeCart();
      if (mergeReport.performed && mergeReport.result !== "NOOP") {
        const mergeMsg =
          mergeReport.result === "ADOPTED"
            ? "We restored your saved cart."
            : "We synced your carts.";
        toast.success(mergeMsg);
      }
      if (mergeReport.warnings.length > 0) {
        let toastId: string | number;
        sessionStorage.setItem(
          "cartMergeWarnings",
          JSON.stringify(mergeReport.warnings),
        );
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

      await refreshCart();

      const claimReport = await claimOrders();
      if (claimReport.claimed_orders > 0) {
        toast.success(
          `We found ${claimReport.claimed_orders} guest order(s) and linked them to your account.`,
        );
      }

      router.push("/products");
    } catch (e: any) {
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
