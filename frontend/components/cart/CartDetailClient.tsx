"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { CartDetail } from "@/components/cart/CartDetail"; // tvůj v0 component (export CartDetail)
import {
  deleteCartItem,
  getCart,
  updateCartItemQuantity,
} from "@/lib/api/cart";
import type { CartVm } from "@/lib/mappers/cart";
import { mapCartToVm } from "@/lib/mappers/cart";
import { hasAccessToken } from "@/lib/auth/client";

type Props = {
  initialCartVm: CartVm;
};

export default function CartDetailClient({ initialCartVm }: Props) {
  const router = useRouter();
  const [cart, setCart] = useState<CartVm>(initialCartVm);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const dto = await getCart();
    setCart(mapCartToVm(dto));
  }, []);

  const onContinueShopping = useCallback(() => {
    router.push("/products");
  }, [router]);

  const onCheckout = useCallback(() => {
    const authed = hasAccessToken();
    router.push(authed ? "/checkout" : "/guest/checkout");
  }, [router]);

  const onRemoveItem = useCallback(
    async (productIdStr: string) => {
      setBusy(true);
      try {
        await deleteCartItem({ productId: Number(productIdStr) });
        await refresh();
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const changeQty = useCallback(
    async (productIdStr: string, nextQty: number) => {
      if (nextQty < 1) return;
      setBusy(true);
      try {
        await updateCartItemQuantity({
          productId: Number(productIdStr),
          quantity: nextQty,
        });
        await refresh();
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const onDecreaseQty = useCallback(
    async (productIdStr: string) => {
      const item = cart.items.find((i) => i.productId === productIdStr);
      if (!item) return;
      await changeQty(productIdStr, item.quantity - 1);
    },
    [cart.items, changeQty],
  );

  const onIncreaseQty = useCallback(
    async (productIdStr: string) => {
      const item = cart.items.find((i) => i.productId === productIdStr);
      if (!item) return;
      await changeQty(productIdStr, item.quantity + 1);
    },
    [cart.items, changeQty],
  );

  const onClearCart = useCallback(async () => {
    // Strategy: delete each item (no dedicated endpoint exists yet)
    setBusy(true);
    try {
      const productIds = cart.items.map((i) => Number(i.productId));
      for (const pid of productIds) {
        await deleteCartItem({ productId: pid });
      }
      await refresh();
    } finally {
      setBusy(false);
    }
  }, [cart.items, refresh]);

  return (
    <div className={busy ? "opacity-70 pointer-events-none" : ""}>
      <CartDetail
        cart={cart}
        onContinueShopping={onContinueShopping}
        onRemoveItem={onRemoveItem}
        onDecreaseQty={onDecreaseQty}
        onIncreaseQty={onIncreaseQty}
        onClearCart={onClearCart}
        onCheckout={onCheckout}
      />
    </div>
  );
}
