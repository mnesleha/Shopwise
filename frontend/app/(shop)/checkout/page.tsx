"use client";

import { useRouter } from "next/navigation";
import { CheckoutForm, type CheckoutValues } from "@/components/checkout/CheckoutForm";
import { checkoutCart } from "@/lib/api/checkout";

export default function CheckoutPage() {
  const router = useRouter();

  const onBackToCart = () => router.push("/cart");

  const onSubmit = async (values: CheckoutValues) => {
    const order = await checkoutCart(values);
    // order detail route – uprav dle svého existujícího routingu
    router.push(`/orders/${order.id}`);
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
