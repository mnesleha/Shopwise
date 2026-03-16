/**
 * useOrderDiscountToast
 *
 * Contract guarded:
 * - Fires toast.success on false → true transition of orderDiscountApplied
 * - Fires toast.success when the winning promotion changes while discount remains applied
 * - Does NOT fire when discount is already active on mount (prevRef seeded from live state)
 * - Does NOT fire on re-render when discount is unchanged (no spurious toasts)
 * - After discount is removed and re-applied, fires again (true → false → true)
 * - Does NOT fire when component remounts while discount is still active
 * - Toast message includes discount amount when available
 * - Toast message is generic when amount is absent
 * - Toast is sticky (duration: Infinity)
 * - Toast is dismissed when the user navigates to a different route (pathname change)
 * - Toast is NOT dismissed when the pathname stays the same
 * - Toast IS dismissed when the component unmounts (navigation away from the host page)
 */
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Module mocks ──────────────────────────────────────────────────────────────

const cartState: {
  orderDiscountApplied: boolean;
  orderDiscountAmount: string | null;
  orderDiscountPromotionName: string | null;
  refreshCart: ReturnType<typeof vi.fn>;
  count: number;
  resetCount: ReturnType<typeof vi.fn>;
} = {
  orderDiscountApplied: false,
  orderDiscountAmount: null,
  orderDiscountPromotionName: null,
  refreshCart: vi.fn(),
  count: 0,
  resetCount: vi.fn(),
};

vi.mock("@/components/cart/CartProvider", () => ({ useCart: () => cartState }));

// Mutable pathname so tests can simulate navigation by mutating this variable.
let currentPathname = "/products";
vi.mock("next/navigation", () => ({ usePathname: () => currentPathname }));

const mockToastSuccess = vi.fn().mockReturnValue("test-toast-id");
const mockToastDismiss = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    dismiss: (...args: unknown[]) => mockToastDismiss(...args),
  },
}));

// Import the hook after mocks are registered.
import { useOrderDiscountToast } from "@/components/cart/useOrderDiscountToast";

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  cartState.orderDiscountApplied = false;
  cartState.orderDiscountAmount = null;
  cartState.orderDiscountPromotionName = null;
  currentPathname = "/products";
  mockToastSuccess.mockClear();
  mockToastDismiss.mockClear();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useOrderDiscountToast", () => {
  describe("toast on false → true transition", () => {
    it("fires toast.success when orderDiscountApplied transitions from false to true", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast());

      expect(mockToastSuccess).not.toHaveBeenCalled();

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();

      expect(mockToastSuccess).toHaveBeenCalledOnce();
    });

    it("toast message contains 'Good news'", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast());

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();

      const message = mockToastSuccess.mock.calls[0]?.[0] as string;
      expect(message).toMatch(/good news/i);
    });

    it("includes the discount amount in the message when amount is > 0", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast());

      act(() => {
        cartState.orderDiscountApplied = true;
        cartState.orderDiscountAmount = "12.50";
      });
      rerender();

      const message = mockToastSuccess.mock.calls[0]?.[0] as string;
      expect(message).toContain("12.50");
    });

    it("uses generic message when discount amount is null", () => {
      cartState.orderDiscountAmount = null;
      const { rerender } = renderHook(() => useOrderDiscountToast());

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();

      const message = mockToastSuccess.mock.calls[0]?.[0] as string;
      expect(message).not.toContain("null");
      expect(message).toMatch(/order discount has been applied/i);
    });

    it("toast is sticky — duration is Infinity", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast());

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();

      const options = mockToastSuccess.mock.calls[0]?.[1] as {
        duration?: number;
      };
      expect(options?.duration).toBe(Infinity);
    });
  });

  describe("no spurious toasts", () => {
    it("does NOT fire when discount is already active on mount (prevRef seeded from live state)", () => {
      cartState.orderDiscountApplied = true;
      renderHook(() => useOrderDiscountToast());

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });

    it("does NOT fire on subsequent re-renders when discount remains true", () => {
      cartState.orderDiscountApplied = true;
      const { rerender } = renderHook(() => useOrderDiscountToast());

      rerender();
      rerender();

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });

    it("does NOT fire when discount stays false across re-renders", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast());

      rerender();
      rerender();

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });

    it("does NOT fire when component remounts while discount is still active", () => {
      // First mount: discount transitions false → true and fires once.
      cartState.orderDiscountApplied = false;
      const { rerender, unmount } = renderHook(() => useOrderDiscountToast());
      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();
      expect(mockToastSuccess).toHaveBeenCalledOnce();
      mockToastSuccess.mockClear();

      // Simulate unmount (navigation away) and remount (back to same page).
      unmount();
      renderHook(() => useOrderDiscountToast());

      // Still active on remount — must NOT fire a second toast.
      expect(mockToastSuccess).not.toHaveBeenCalled();
    });
  });

  describe("re-application after removal", () => {
    it("fires again when discount is removed and then re-applied", () => {
      // Initial mount: discount active, prevRef seeded from live state → no toast
      cartState.orderDiscountApplied = true;
      const { rerender } = renderHook(() => useOrderDiscountToast());
      expect(mockToastSuccess).not.toHaveBeenCalled();

      // Discount removed
      act(() => {
        cartState.orderDiscountApplied = false;
      });
      rerender();
      expect(mockToastSuccess).not.toHaveBeenCalled();

      // Discount re-applied
      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();
      expect(mockToastSuccess).toHaveBeenCalledOnce();
    });
  });

  describe("toast on winner change (promotion name changes while discount stays applied)", () => {
    it("fires a new toast when the winning promotion changes while discount remains applied", () => {
      // Initial mount: discount active with OL-Percent-40
      cartState.orderDiscountApplied = true;
      cartState.orderDiscountPromotionName = "OL-Percent-40";
      const { rerender } = renderHook(() => useOrderDiscountToast());
      // No toast on initial mount (prevRef seeded)
      expect(mockToastSuccess).not.toHaveBeenCalled();

      // Winner changes to OL-Fixed-500 while discount still applied
      act(() => {
        cartState.orderDiscountPromotionName = "OL-Fixed-500";
      });
      rerender();

      expect(mockToastSuccess).toHaveBeenCalledOnce();
    });

    it("dismisses the previous toast before firing the winner-change toast", () => {
      // Start with discount off, then gain it with promotion A
      const { rerender } = renderHook(() => useOrderDiscountToast());
      act(() => {
        cartState.orderDiscountApplied = true;
        cartState.orderDiscountPromotionName = "OL-Percent-40";
      });
      rerender();
      // First toast fired (false → true)
      expect(mockToastSuccess).toHaveBeenCalledOnce();
      mockToastDismiss.mockClear();

      // Winner changes
      act(() => {
        cartState.orderDiscountPromotionName = "OL-Fixed-500";
      });
      rerender();

      // Old toast should have been dismissed before the new one fires
      expect(mockToastDismiss).toHaveBeenCalledWith("test-toast-id");
      expect(mockToastSuccess).toHaveBeenCalledTimes(2);
    });

    it("does NOT fire when promotion name stays the same on re-render", () => {
      cartState.orderDiscountApplied = true;
      cartState.orderDiscountPromotionName = "OL-Percent-40";
      const { rerender } = renderHook(() => useOrderDiscountToast());

      rerender();
      rerender();

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });

    it("does NOT fire when promotionName is null even if discount is applied", () => {
      cartState.orderDiscountApplied = true;
      cartState.orderDiscountPromotionName = null;
      const { rerender } = renderHook(() => useOrderDiscountToast());

      rerender();

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });
  });

  describe("navigation dismissal", () => {
    it("dismisses the sticky toast when the user navigates to a different route", () => {
      // Fire the toast first.
      const { rerender } = renderHook(() => useOrderDiscountToast());
      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();
      expect(mockToastSuccess).toHaveBeenCalledOnce();

      // Simulate navigation.
      act(() => {
        currentPathname = "/checkout";
      });
      rerender();

      expect(mockToastDismiss).toHaveBeenCalledWith("test-toast-id");
    });

    it("does NOT dismiss the toast while the pathname stays the same", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast());
      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();
      // Multiple re-renders with the same pathname — no dismiss expected.
      rerender();
      rerender();

      expect(mockToastDismiss).not.toHaveBeenCalled();
    });

    it("does NOT call dismiss if no toast was shown before navigation", () => {
      // Discount never applies — no toast fired.
      const { rerender } = renderHook(() => useOrderDiscountToast());

      act(() => {
        currentPathname = "/checkout";
      });
      rerender();

      expect(mockToastDismiss).not.toHaveBeenCalled();
    });

    it("dismisses the toast when the component unmounts (page navigation)", () => {
      // Fire the toast first.
      const { rerender, unmount } = renderHook(() => useOrderDiscountToast());
      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();
      expect(mockToastSuccess).toHaveBeenCalledOnce();
      mockToastDismiss.mockClear();

      // Unmount (e.g. user navigates away from /products to /cart).
      unmount();

      expect(mockToastDismiss).toHaveBeenCalledWith("test-toast-id");
    });

    it("does NOT call dismiss on unmount when no toast was shown", () => {
      // Discount never applied during this mount.
      const { unmount } = renderHook(() => useOrderDiscountToast());
      unmount();

      expect(mockToastDismiss).not.toHaveBeenCalled();
    });
  });
});
