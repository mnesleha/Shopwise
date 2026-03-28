"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getOrder } from "@/lib/api/orders";
import {
  loadAndClearPaymentReturnContext,
  type PaymentReturnContext,
} from "@/lib/utils/paymentReturn";

// ---------------------------------------------------------------------------
// Return-page state machine
// ---------------------------------------------------------------------------
//
// loading           — initial; reading sessionStorage and (for auth) fetching
//                     order status from the backend
// pending           — order is CREATED (webhook not processed yet)
// paid              — order is PAID; auto-navigates to order detail
// failed            — order is PAYMENT_FAILED
// guest_success     — guest checkout; direct the user to their email access link
// no_context        — direct navigation without prior checkout redirect

type ReturnState =
  | "loading"
  | "pending"
  | "paid"
  | "failed"
  | "guest_success"
  | "no_context";

export default function PaymentReturnPage() {
  const router = useRouter();
  const [state, setState] = useState<ReturnState>("loading");
  const [ctx, setCtx] = useState<PaymentReturnContext | null>(null);

  const fetchOrderState = useCallback(async (context: PaymentReturnContext) => {
    try {
      const order = await getOrder(context.orderId);
      if (order.status === "PAID") {
        setState("paid");
      } else if (order.status === "PAYMENT_FAILED") {
        setState("failed");
      } else {
        // CREATED or another status means the webhook has not been processed
        // yet.  Show the pending state.
        setState("pending");
      }
    } catch {
      // Network / auth error — treat as pending so the user can retry
      setState("pending");
    }
  }, []);

  useEffect(() => {
    const context = loadAndClearPaymentReturnContext();
    if (!context) {
      setState("no_context");
      return;
    }
    setCtx(context);

    if (context.isGuest) {
      setState("guest_success");
      return;
    }

    // Authenticated: fetch backend truth
    fetchOrderState(context);
  }, [fetchOrderState]);

  // Navigate to the order detail page once payment is confirmed
  useEffect(() => {
    if (state === "paid" && ctx) {
      router.push(`/orders/${ctx.orderId}`);
    }
  }, [state, ctx, router]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (state === "loading") {
    return (
      <div className="space-y-3" data-testid="payment-return-loading">
        <h1 className="text-2xl font-semibold">Checking your payment…</h1>
        <p className="text-muted-foreground">
          Please wait while we confirm your payment status.
        </p>
      </div>
    );
  }

  if (state === "paid") {
    // Brief transitional state while useEffect above triggers router.push
    return (
      <div className="space-y-3" data-testid="payment-return-paid">
        <h1 className="text-2xl font-semibold">Payment confirmed</h1>
        <p className="text-muted-foreground">
          Your payment was successful. Redirecting to your order…
        </p>
      </div>
    );
  }

  if (state === "guest_success") {
    return (
      <div className="space-y-3" data-testid="payment-return-guest-success">
        <h1 className="text-2xl font-semibold">Check your email</h1>
        <p className="text-muted-foreground">
          Your guest order was created successfully. We sent an order access
          link to your email so you can open the order details.
        </p>
        <p className="text-muted-foreground">
          If you do not see it yet, check your spam folder before continuing.
        </p>
        <button
          onClick={() => router.push("/products")}
          className="underline underline-offset-4 text-sm font-medium"
        >
          Continue shopping
        </button>
      </div>
    );
  }

  if (state === "pending") {
    return (
      <div className="space-y-3" data-testid="payment-return-pending">
        <h1 className="text-2xl font-semibold">Payment is being processed</h1>
        <p className="text-muted-foreground">
          Your payment is still being confirmed by the payment provider. This
          usually takes just a moment.
        </p>
        <p className="text-muted-foreground">
          You can check the status of your order at any time from your{" "}
          <button
            onClick={() => router.push("/orders")}
            className="underline underline-offset-4 font-medium"
          >
            orders page
          </button>
          .
        </p>
        {ctx && (
          <button
            data-testid="payment-return-check-again"
            onClick={() => {
              setState("loading");
              fetchOrderState(ctx);
            }}
            className="underline underline-offset-4 text-sm font-medium"
          >
            Check again
          </button>
        )}
      </div>
    );
  }

  if (state === "failed") {
    return (
      <div className="space-y-3" data-testid="payment-return-failed">
        <h1 className="text-2xl font-semibold">Payment failed</h1>
        <p className="text-muted-foreground">
          Your payment could not be processed. No charge has been made.
        </p>
        <p className="text-muted-foreground">
          Please try again or contact our support if the issue persists.
        </p>
        <div className="flex gap-4">
          <button
            data-testid="payment-return-back-to-cart"
            onClick={() => router.push("/cart")}
            className="underline underline-offset-4 text-sm font-medium"
          >
            Back to cart
          </button>
          {ctx && (
            <button
              data-testid="payment-return-view-order"
              onClick={() => router.push(`/orders/${ctx.orderId}`)}
              className="underline underline-offset-4 text-sm font-medium"
            >
              View order
            </button>
          )}
        </div>
      </div>
    );
  }

  // no_context — direct navigation or stale tab
  return (
    <div className="space-y-3" data-testid="payment-return-no-context">
      <h1 className="text-2xl font-semibold">Nothing to confirm here</h1>
      <p className="text-muted-foreground">
        We could not find a pending payment to confirm. If you just placed an
        order, check your{" "}
        <button
          onClick={() => router.push("/orders")}
          className="underline underline-offset-4 font-medium"
        >
          orders
        </button>{" "}
        to see its status.
      </p>
    </div>
  );
}
