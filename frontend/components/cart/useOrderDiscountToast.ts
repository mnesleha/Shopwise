/**
 * useOrderDiscountToast
 *
 * Fires a positive Sonner toast exactly once when the cart transitions from
 * having no auto-applied order-level discount to having one.
 *
 * Call sites must pass `initialApplied = true` when the server-rendered cart
 * already has an active discount so that the initial state is silently synced
 * without displaying a spurious toast on mount.
 *
 * Guard behaviour:
 * - No toast on initial render, regardless of the discount state.
 * - Toast fires only on the false → true transition during the current
 *   browsing session (tracked via a React ref, not persisted across page
 *   refreshes).
 * - The toast auto-dismisses after 8 seconds; the user can also close it
 *   manually.  It is NOT shown again until the discount is removed and
 *   re-applied within the same session.
 */

"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { usePathname } from "next/navigation";
import { useCart } from "@/components/cart/CartProvider";

export function useOrderDiscountToast(initialApplied = false): void {
  const { orderDiscountApplied, orderDiscountAmount } = useCart();
  const pathname = usePathname();

  /**
   * prevRef tracks the last known discount state so we can detect the
   * false → true edge.  Initialised from the server-rendered state so that
   * a discount already active on mount does not trigger a toast.
   */
  const prevRef = useRef<boolean>(initialApplied);

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

  // Dismiss the sticky toast when the user navigates to a different page.
  useEffect(() => {
    if (prevPathnameRef.current !== pathname && toastIdRef.current !== null) {
      toast.dismiss(toastIdRef.current);
      toastIdRef.current = null;
    }
    prevPathnameRef.current = pathname;
  }, [pathname]);

  useEffect(() => {
    if (!prevRef.current && orderDiscountApplied) {
      const msg =
        orderDiscountAmount && parseFloat(orderDiscountAmount) > 0
          ? `Good news — a ${orderDiscountAmount} discount has been applied to your order.`
          : "Good news — your order discount has been applied.";

      // The toast is sticky (duration: Infinity) so the user can read it
      // at their own pace.  It is dismissed either manually (closeButton)
      // or automatically when a pathname change is detected above.
      const id = toast.success(msg, {
        duration: Infinity,
        closeButton: true,
      });
      toastIdRef.current = id;
    }
    prevRef.current = orderDiscountApplied;
  }, [orderDiscountApplied, orderDiscountAmount]);
}
