"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { ProductDetail } from "@/components/product/ProductDetail";
import { api } from "@/lib/api";
import { addCartItem } from "@/lib/api/cart";

type Props = {
  product: {
    id: string;
    name: string;
    description?: string;
    price: string;
    currency?: string;
    stockQuantity: number;
    images?: string[];
    specs?: Array<{ label: string; value: string }>;
  };
};

export default function ProductDetailClient({ product }: Props) {
  const router = useRouter();

  const onBack = useCallback(() => {
    router.push("/products");
  }, [router]);

const onAddToCart = useCallback(
  async (productId: string) => {
    await addCartItem({ productId: Number(productId), quantity: 1 });
    router.push("/cart");
  },
  [router]
);

  return <ProductDetail product={product} onBack={onBack} onAddToCart={onAddToCart} />;
}
