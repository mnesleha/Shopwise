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
  /**
   * Phase 4 / Slice 3: whether an AUTO_APPLY order-level discount is currently
   * applied to the cart.  Starts false and is updated on every refreshCart().
   */
  orderDiscountApplied: boolean;
  /**
   * Gross reduction amount as a decimal string, or null when no order-level
   * discount is applied.  Updated in sync with orderDiscountApplied.
   */
  orderDiscountAmount: string | null;
  /**
   * Human-readable name of the currently winning order-level promotion, or
   * null.  Used by useOrderDiscountToast to detect winner changes.
   */
  orderDiscountPromotionName: string | null;
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
  const [orderDiscountApplied, setOrderDiscountApplied] = useState(false);
  const [orderDiscountAmount, setOrderDiscountAmount] = useState<string | null>(
    null,
  );
  const [orderDiscountPromotionName, setOrderDiscountPromotionName] = useState<
    string | null
  >(null);

  const refreshCart = useCallback(async () => {
    try {
      const cart = await getCart();
      const total = cart.items.reduce((sum, it) => sum + it.quantity, 0);
      setCount(total);
      setOrderDiscountApplied(cart.totals?.order_discount_applied ?? false);
      setOrderDiscountAmount(cart.totals?.order_discount_amount ?? null);
      setOrderDiscountPromotionName(
        cart.totals?.order_discount_promotion_name ?? null,
      );
    } catch {
      setCount(0);
      setOrderDiscountApplied(false);
      setOrderDiscountAmount(null);
      setOrderDiscountPromotionName(null);
    }
  }, []);

  const resetCount = useCallback(() => setCount(0), []);

  const value = useMemo(
    () => ({
      count,
      refreshCart,
      resetCount,
      orderDiscountApplied,
      orderDiscountAmount,
      orderDiscountPromotionName,
    }),
    [
      count,
      refreshCart,
      resetCount,
      orderDiscountApplied,
      orderDiscountAmount,
      orderDiscountPromotionName,
    ],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
