"use client";

import { useEffect, useState } from "react";
import CartDetailClient from "@/components/cart/CartDetailClient";
import { getCart } from "@/lib/api/cart";
import { mapCartToVm, type CartVm } from "@/lib/mappers/cart";

export default function CartPage() {
  const [cart, setCart] = useState<CartVm | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getCart()
      .then((dto) => setCart(mapCartToVm(dto)))
      .catch((e) => setErr(String(e?.message ?? e)));
  }, []);

  if (err) return <pre className="whitespace-pre-wrap">ERROR: {err}</pre>;
  if (!cart) return <p>Loading cart…</p>;

  return <CartDetailClient initialCartVm={cart} />;
}
