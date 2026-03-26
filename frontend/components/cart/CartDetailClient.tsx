"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { CartDetail } from "@/components/cart/CartDetail";
import {
  addCartItem,
  clearCart,
  deleteCartItem,
  getCart,
  updateCartItemQuantity,
} from "@/lib/api/cart";
import type { CartMergeWarning } from "@/lib/api/cart";
import type { CartVm } from "@/lib/mappers/cart";
import { mapCartToVm } from "@/lib/mappers/cart";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";
import { useOrderDiscountToast } from "@/components/cart/useOrderDiscountToast";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

type Props = {
  initialCartVm: CartVm;
};

export default function CartDetailClient({ initialCartVm }: Props) {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { refreshCart } = useCart();
  const [cart, setCart] = useState<CartVm>(initialCartVm);
  const [busy, setBusy] = useState(false);

  // Show a positive toast when an order-level discount is newly applied.
  // The hook reads current cart state from the CartProvider; call without args.
  useOrderDiscountToast();

  // ── Stock-adjustment warnings (one-time, from sessionStorage) ────────────
  const [mergeWarnings, setMergeWarnings] = useState<CartMergeWarning[]>([]);

  useEffect(() => {
    const raw = sessionStorage.getItem("cartMergeWarnings");
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as CartMergeWarning[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMergeWarnings(parsed);
        }
      } catch {
        // ignore malformed data
      }
      // Remove immediately — display is one-time only
      sessionStorage.removeItem("cartMergeWarnings");
    }
  }, []);

  /** Map from productId string → { requested, applied } for badge rendering */
  const adjustedItems = useMemo(
    () =>
      new Map(
        mergeWarnings.map((w) => [
          String(w.product_id),
          { requested: w.requested, applied: w.applied },
        ]),
      ),
    [mergeWarnings],
  );

  const refresh = useCallback(async () => {
    const dto = await getCart();
    setCart(mapCartToVm(dto));
    await refreshCart();
  }, [refreshCart]);

  const onContinueShopping = useCallback(() => {
    router.push("/products");
  }, [router]);

  const onCheckout = useCallback(() => {
    router.push(isAuthenticated ? "/checkout" : "/guest/checkout");
  }, [router, isAuthenticated]);

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
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response
          ?.status;
        if (status === 409) {
          toast.error("Not enough stock available.");
        } else {
          toast.error("Could not update quantity. Please try again.");
        }
        // Re-sync local cart state even on error so the UI stays consistent.
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
    const snapshot = cart.items.map((item) => ({
      productId: Number(item.productId),
      productName: item.productName,
      quantity: item.quantity,
    }));

    const restoreClearedCart = async () => {
      setBusy(true);
      try {
        for (const item of snapshot) {
          await addCartItem({
            productId: item.productId,
            quantity: item.quantity,
          });
        }
        await refresh();
        toast.success("Cart restored.");
      } catch {
        toast.error("Could not restore cart. Please try again.");
        await refresh();
      } finally {
        setBusy(false);
      }
    };

    setBusy(true);
    try {
      await clearCart();
      await refresh();
      toast.success("Cart cleared.", {
        duration: 12000,
        action: {
          label: "Undo",
          onClick: () => {
            void restoreClearedCart();
          },
        },
      });
    } finally {
      setBusy(false);
    }
  }, [cart.items, refresh]);

  return (
    <div className={busy ? "opacity-70 pointer-events-none" : ""}>
      {/* Stock-adjustment banner — shown once after a merge with warnings */}
      {mergeWarnings.length > 0 && (
        <Alert
          className="mb-4 border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/40"
          data-testid="cart-merge-adjustment-banner"
        >
          <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          <AlertTitle>Stock adjustments applied</AlertTitle>
          <AlertDescription>
            We updated quantities to match current availability.
            {mergeWarnings.length <= 5 && (
              <ul className="mt-1 list-disc pl-4 text-xs">
                {mergeWarnings.map((w) => {
                  const name =
                    cart.items.find((i) => i.productId === String(w.product_id))
                      ?.productName ?? `Product ${w.product_id}`;
                  return (
                    <li key={w.product_id}>
                      {name}: {w.requested} → {w.applied}
                    </li>
                  );
                })}
              </ul>
            )}
          </AlertDescription>
        </Alert>
      )}
      <CartDetail
        cart={cart}
        adjustedItems={adjustedItems}
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
