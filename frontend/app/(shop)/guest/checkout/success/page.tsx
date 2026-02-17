"use client";

import { useRouter } from "next/navigation";
import { CheckoutSuccess } from "@/components/checkout/CheckoutSuccess";

export default function CheckoutSuccessPage() {
  const router = useRouter();

  return (
    <CheckoutSuccess onContinueShopping={() => router.push("/products")} />
  );
}
