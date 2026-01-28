"use client";

import { useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ProductGrid } from "@/components/product/ProductGrid";
import { addCartItem } from "@/lib/api/cart";

export type ProductGridItem = {
  id: string;
  name: string;
  shortDescription?: string;
  price: string;
  currency?: string;
  stockQuantity: number;
  imageUrl?: string;
};

type Props = {
  products: ProductGridItem[];
  page: number;
  pageSize: number;
  totalItems: number;
};

export default function ProductGridClient({
  products,
  page,
  pageSize,
  totalItems,
}: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const setQuery = useCallback(
    (next: { page?: number; pageSize?: number }) => {
      const sp = new URLSearchParams(searchParams?.toString() ?? "");
      if (next.page !== undefined) sp.set("page", String(next.page));
      if (next.pageSize !== undefined) sp.set("pageSize", String(next.pageSize));
      router.push(`/products?${sp.toString()}`);
    },
    [router, searchParams]
  );

  const onPageChange = useCallback(
    (nextPage: number) => {
      setQuery({ page: nextPage });
    },
    [setQuery]
  );

  const onOpenProduct = useCallback(
    (productId: string) => {
      router.push(`/products/${productId}`);
    },
    [router]
  );

  const onAddToCart = useCallback(
    async (productId: string) => {
      await addCartItem({ productId: Number(productId), quantity: 1 });
      router.push("/cart");
    },
    [router]
  );


  return (
    <ProductGrid
      products={products}
      page={page}
      pageSize={pageSize}
      totalItems={totalItems}
      onPageChange={onPageChange}
      onAddToCart={onAddToCart}
      onOpenProduct={onOpenProduct}
    />
  );
}
