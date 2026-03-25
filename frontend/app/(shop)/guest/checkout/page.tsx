"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  CheckoutForm,
  type CheckoutValues,
} from "@/components/checkout/CheckoutForm";
import { checkoutCart } from "@/lib/api/checkout";
import { savePaymentReturnContext } from "@/lib/utils/paymentReturn";
import { useCart } from "@/components/cart/CartProvider";

export default function GuestCheckoutPage() {
  const router = useRouter();
  const { resetCount } = useCart();

  const onSubmit = async (values: CheckoutValues) => {
    try {
      const order = await checkoutCart(values);
      resetCount();

      if (
        order.payment_initiation.payment_flow === "REDIRECT" &&
        order.payment_initiation.redirect_url
      ) {
        // Hosted/redirect flow: save context so the return page knows this was
        // a guest order, then hand the browser off to the payment provider.
        savePaymentReturnContext({ orderId: order.id, isGuest: true });
        window.location.assign(order.payment_initiation.redirect_url);
      } else {
        // Direct flow (e.g. COD): payment is applied synchronously at checkout.
        router.push("/guest/checkout/success");
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
        <h1 className="text-2xl font-semibold">Guest Checkout</h1>
        <p className="text-muted-foreground">
          We’ll email you an order access link after placing the order.
        </p>
      </div>

      <CheckoutForm
        onBackToCart={() => router.push("/cart")}
        onSubmit={onSubmit}
      />
    </div>
  );
}
