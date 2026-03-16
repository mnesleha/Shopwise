/**
 * useOrderDiscountToast
 *
 * Fires a positive Sonner toast whenever the cart gains (or changes) an
 * auto-applied order-level discount:
 *
 * - No toast on initial render, regardless of the discount state.
 * - Toast fires on the false → true transition of orderDiscountApplied.
 * - Toast also fires when the *winning promotion changes* while
 *   orderDiscountApplied remains true (e.g. cart crosses a higher threshold).
 * - Initialises from the current live cart state so that remounting the host
 *   component never produces a duplicate toast.
 * - The sticky toast is automatically dismissed on unmount, on pathname change,
 *   or when the user closes it manually.
 * - Fires again only if the discount is removed and then re-applied within
 *   the same component lifetime.
 */

"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { usePathname } from "next/navigation";
import { useCart } from "@/components/cart/CartProvider";

export function useOrderDiscountToast(): void {
  const { orderDiscountApplied, orderDiscountAmount, orderDiscountPromotionName } = useCart();
  const pathname = usePathname();

  /**
   * prevRef tracks the last known discount state so we can detect the
   * false → true edge.  Initialised from the *current* live cart state so
   * that remounting the component while an active discount is already present
   * does not trigger a spurious toast.
   */
  const prevRef = useRef<boolean>(orderDiscountApplied);

  /**
   * prevNameRef tracks the last known winning promotion name so we can detect
   * a winner-change while the discount remains applied.
   */
  const prevNameRef = useRef<string | null>(orderDiscountPromotionName);

  /**
   * toastIdRef stores the ID of the active sticky toast so we can
   * programmatically dismiss it when the user navigates away.
   */
  const toastIdRef = useRef<string | number | null>(null);

  /**
   * prevPathnameRef seeds from the current pathname on mount so that
   * the very first render never triggers a spurious dismiss.
   */
  const prevPathnameRef = useRef<string>(pathname);

  // Dismiss the sticky toast when the host component unmounts (e.g. the user
  // navigates away from the page that renders this hook).
  useEffect(() => {
    return () => {
      if (toastIdRef.current !== null) {
        toast.dismiss(toastIdRef.current);
        toastIdRef.current = null;
      }
    };
  }, []);

  // Dismiss the sticky toast when the user navigates to a different page
  // while the component remains mounted.
  useEffect(() => {
    if (prevPathnameRef.current !== pathname && toastIdRef.current !== null) {
      toast.dismiss(toastIdRef.current);
      toastIdRef.current = null;
    }
    prevPathnameRef.current = pathname;
  }, [pathname]);

  useEffect(() => {
    const gainedDiscount = !prevRef.current && orderDiscountApplied;
    const winnerChanged =
      orderDiscountApplied &&
      prevRef.current &&
      orderDiscountPromotionName !== null &&
      prevNameRef.current !== orderDiscountPromotionName;

    if (gainedDiscount || winnerChanged) {
      // Dismiss the previous sticky toast before firing a new one so we never
      // accumulate stale toasts when the winner changes.
      if (toastIdRef.current !== null) {
        toast.dismiss(toastIdRef.current);
        toastIdRef.current = null;
      }

      const msg =
        orderDiscountAmount && parseFloat(orderDiscountAmount) > 0
          ? `Good news — a ${orderDiscountAmount} discount has been applied to your order.`
          : "Good news — your order discount has been applied.";

      // The toast is sticky (duration: Infinity) so the user can read it
      // at their own pace.  It is dismissed on unmount, on pathname change,
      // or manually via the close button.
      const id = toast.success(msg, {
        duration: Infinity,
        closeButton: true,
      });
      toastIdRef.current = id;
    }

    prevRef.current = orderDiscountApplied;
    prevNameRef.current = orderDiscountPromotionName;
  }, [orderDiscountApplied, orderDiscountAmount, orderDiscountPromotionName]);
}
