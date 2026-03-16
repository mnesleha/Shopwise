"use client";

import { useRef, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  CheckoutForm,
  type CheckoutValues,
} from "@/components/checkout/CheckoutForm";
import {
  checkoutCart,
  getCheckoutPreflight,
  type PriceChangePayload,
} from "@/lib/api/checkout";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";
import { getPriceChangeMessage } from "@/lib/utils/priceChange";

export default function CheckoutPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { resetCount } = useCart();
  const isAuthenticatedRef = useRef(isAuthenticated);
  useEffect(() => {
    isAuthenticatedRef.current = isAuthenticated;
  }, [isAuthenticated]);

  /** Non-null when preflight reports a WARNING-level price change. */
  const [warningPayload, setWarningPayload] =
    useState<PriceChangePayload | null>(null);

  // ── Run preflight check when the page first mounts ────────────────────────
  useEffect(() => {
    // `cancelled` ensures that when React Strict Mode runs cleanup + re-mount,
    // only the second mount's promise result is acted on (prevents double toast).
    let cancelled = false;
    getCheckoutPreflight()
      .then((preflight) => {
        if (cancelled) return;
        if (preflight.severity === "WARNING") {
          setWarningPayload(preflight);
        } else if (preflight.severity === "INFO") {
          const msg = getPriceChangeMessage(preflight);
          if (msg) toast.info(msg);
        }
      })
      .catch(() => {
        // No active cart or network error — silently ignore so the form renders.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /** Resolve the post-checkout navigation target for a given order id. */
  const orderTarget = (id: number) =>
    isAuthenticatedRef.current ? `/orders/${id}` : "/guest/checkout/success";

  const onBackToCart = () => router.push("/cart");

  const onSubmit = async (values: CheckoutValues) => {
    const order = await checkoutCart(values);
    resetCount();
    router.push(orderTarget(order.id));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Checkout</h1>
        <p className="text-muted-foreground">
          Shipping and payment are simulated in this demo.
        </p>
      </div>

      <CheckoutForm
        onBackToCart={onBackToCart}
        onSubmit={onSubmit}
        priceChangePayload={warningPayload}
      />
    </div>
  );
}
