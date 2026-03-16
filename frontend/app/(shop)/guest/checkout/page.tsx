"use client";

import { useRouter } from "next/navigation";
import {
  CheckoutForm,
  type CheckoutValues,
} from "@/components/checkout/CheckoutForm";
import { checkoutCart } from "@/lib/api/checkout";
import { useCart } from "@/components/cart/CartProvider";

export default function GuestCheckoutPage() {
  const router = useRouter();
  const { resetCount } = useCart();

  const onSubmit = async (values: CheckoutValues) => {
    await checkoutCart(values);
    resetCount();
    router.push("/guest/checkout/success");
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
