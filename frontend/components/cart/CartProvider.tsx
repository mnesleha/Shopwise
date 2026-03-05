"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import { getCart } from "@/lib/api/cart";

type CartState = {
  count: number;
  refreshCart: () => Promise<void>;
  /** Zero the badge synchronously without an API call (e.g. after logout/password-change). */
  resetCount: () => void;
};

const CartContext = createContext<CartState | null>(null);

export function CartProvider({
  children,
  initialCount = 0,
}: {
  children: React.ReactNode;
  initialCount?: number;
}) {
  const [count, setCount] = useState(initialCount);

  const refreshCart = useCallback(async () => {
    try {
      const cart = await getCart();
      const total = cart.items.reduce((sum, it) => sum + it.quantity, 0);
      setCount(total);
    } catch {
      setCount(0);
    }
  }, []);

  const resetCount = useCallback(() => setCount(0), []);

  const value = useMemo(
    () => ({ count, refreshCart, resetCount }),
    [count, refreshCart, resetCount],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
