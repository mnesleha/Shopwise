"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ProductDetail } from "@/components/product/ProductDetail";
import { api } from "@/lib/api";
import { addCartItem } from "@/lib/api/cart";
import { useCart } from "@/components/cart/CartProvider";
import type { ProductImageVm } from "@/lib/mappers/products";

type Props = {
  product: {
    id: string;
    name: string;
    shortDescription: string;
    fullDescription: string;
    description?: string;
    price: string;
    currency?: string;
    stockQuantity: number;
    images?: string[];
    gallery?: ProductImageVm[];
    specs?: Array<{ label: string; value: string }>;
  };
};

export default function ProductDetailClient({ product }: Props) {
  const router = useRouter();

  const onBack = useCallback(() => {
    router.push("/products");
  }, [router]);

  const { refreshCart } = useCart();

  const onAddToCart = useCallback(
    async (productId: string) => {
      await addCartItem({ productId: Number(productId), quantity: 1 });
      toast.success(`${product.name} added to cart.`);
      await refreshCart();
      // No redirect — the user stays on the product page.
      // The cart badge updates as additional feedback.
    },
    [product.name, refreshCart],
  );

  return (
    <ProductDetail
      product={product}
      onBack={onBack}
      onAddToCart={onAddToCart}
    />
  );
}
