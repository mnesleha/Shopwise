"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ProductGrid } from "@/components/product/ProductGrid";
import { addCartItem } from "@/lib/api/cart";
import { useCart } from "@/components/cart/CartProvider";
import { useOrderDiscountToast } from "@/components/cart/useOrderDiscountToast";

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
  searchParamsString: string;
};

export default function ProductGridClient({
  products,
  page,
  pageSize,
  totalItems,
  searchParamsString,
}: Props) {
  const router = useRouter();

  const setQuery = useCallback(
    (next: { page?: number; pageSize?: number }) => {
      const sp = new URLSearchParams(searchParamsString);
      if (next.page !== undefined) sp.set("page", String(next.page));
      if (next.pageSize !== undefined)
        sp.set("pageSize", String(next.pageSize));
      router.push(`/products?${sp.toString()}`);
    },
    [router, searchParamsString],
  );

  const onPageChange = useCallback(
    (nextPage: number) => {
      setQuery({ page: nextPage });
    },
    [setQuery],
  );

  const onOpenProduct = useCallback(
    (productId: string) => {
      router.push(`/products/${productId}`);
    },
    [router],
  );

  const { refreshCart } = useCart();

  // Show a positive toast when an order-level discount is newly applied.
  useOrderDiscountToast();

  const onAddToCart = useCallback(
    async (productId: string) => {
      await addCartItem({ productId: Number(productId), quantity: 1 });
      const addedProduct = products.find((product) => product.id === productId);
      toast.success(
        addedProduct
          ? `${addedProduct.name} added to cart.`
          : "Product added to cart.",
      );
      await refreshCart();
      // No redirect — the user stays on the catalogue to continue shopping.
      // The cart badge updates as feedback; the toast hook fires if a new
      // order-level discount was triggered by crossing a spend threshold.
    },
    [products, refreshCart],
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
