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
import { savePaymentReturnContext } from "@/lib/utils/paymentReturn";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";
import { getPriceChangeMessage } from "@/lib/utils/priceChange";
import { getProfile, listAddresses } from "@/lib/api/profile";
import { buildCheckoutPrefill } from "@/lib/utils/buildCheckoutPrefill";

export default function CheckoutPage() {
  const router = useRouter();
  const { isAuthenticated, email } = useAuth();
  const { resetCount } = useCart();
  const isAuthenticatedRef = useRef(isAuthenticated);
  useEffect(() => {
    isAuthenticatedRef.current = isAuthenticated;
  }, [isAuthenticated]);

  /** Non-null when preflight reports a WARNING-level price change. */
  const [warningPayload, setWarningPayload] =
    useState<PriceChangePayload | null>(null);

  // ── Profile prefill for authenticated users ────────────────────────────────
  // `null` means "still loading" (blocks form render); `{}` means ready with no
  // prefill; `{...data}` means ready with prefill values.
  // Auth state is hydrated from SSR so isAuthenticated is stable on first render.
  const [prefill, setPrefill] = useState<Partial<CheckoutValues> | null>(() =>
    isAuthenticated ? null : {},
  );

  useEffect(() => {
    if (!isAuthenticated) {
      setPrefill({});
      return;
    }

    let cancelled = false;
    Promise.all([getProfile(), listAddresses()])
      .then(([profile, addresses]) => {
        if (cancelled) return;
        setPrefill(buildCheckoutPrefill({ profile, addresses, email }));
      })
      .catch(() => {
        // On error, render without prefill rather than blocking the checkout.
        if (!cancelled) setPrefill({});
      });
    return () => {
      cancelled = true;
    };
    // Run once after mount only. isAuthenticated is stable from SSR hydration.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    try {
      const order = await checkoutCart(values);
      resetCount();

      if (
        order.payment_initiation.payment_flow === "REDIRECT" &&
        order.payment_initiation.redirect_url
      ) {
        // Hosted/redirect flow: save context so the return page knows which
        // order to check, then hand the browser off to the payment provider.
        savePaymentReturnContext({ orderId: order.id, isGuest: false });
        window.location.assign(order.payment_initiation.redirect_url);
      } else {
        // Direct flow (e.g. COD): payment is applied synchronously at checkout.
        router.push(orderTarget(order.id));
      }
    } catch (err: unknown) {
      const response = (
        err as { response?: { status?: number; data?: { code?: string } } }
      )?.response;
      const status = response?.status;
      const code = response?.data?.code;

      if (status === 409 && code === "OUT_OF_STOCK") {
        toast.error(
          "One or more items are out of stock. Please review your cart.",
        );
      } else if (status === 409) {
        toast.error("Checkout failed. Please try again.");
      } else {
        toast.error("Something went wrong. Please try again.");
      }
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Checkout</h1>
        <p className="text-muted-foreground">
          Shipping and payment are simulated in this demo.
        </p>
      </div>

      {prefill === null ? null : (
        <CheckoutForm
          initialValues={prefill}
          onBackToCart={onBackToCart}
          onSubmit={onSubmit}
          priceChangePayload={warningPayload}
          isAuthenticated={isAuthenticated}
        />
      )}
    </div>
  );
}
