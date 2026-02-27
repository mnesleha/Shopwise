"use client";

import { useCart } from "@/components/cart/CartProvider";

export function CartBadgeClient() {
  const { count } = useCart();
  if (count <= 0) return null;
  return (
    <span
      className="absolute -right-2 -top-2 min-w-4 h-4 px-1 rounded-full bg-primary text-white text-[10px] leading-4 text-center"
      aria-label={`Cart items: ${count}`}
    >
      {count}
    </span>
  );
}
