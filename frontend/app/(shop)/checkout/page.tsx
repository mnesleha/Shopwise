"use client";

import { useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  CheckoutForm,
  type CheckoutValues,
} from "@/components/checkout/CheckoutForm";
import { checkoutCart } from "@/lib/api/checkout";
import { useAuth } from "@/components/auth/AuthProvider";

export default function CheckoutPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const isAuthenticatedRef = useRef(isAuthenticated);
  useEffect(() => {
    isAuthenticatedRef.current = isAuthenticated;
  }, [isAuthenticated]);

  const onBackToCart = () => router.push("/cart");

  const onSubmit = async (values: CheckoutValues) => {
    const order = await checkoutCart(values);
    router.push(
      isAuthenticatedRef.current
        ? `/orders/${order.id}`
        : "/guest/checkout/success",
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Checkout</h1>
        <p className="text-muted-foreground">
          Shipping and payment are simulated in this demo.
        </p>
      </div>

      <CheckoutForm onBackToCart={onBackToCart} onSubmit={onSubmit} />
    </div>
  );
}
