/**
 * useOrderDiscountToast
 *
 * Contract guarded:
 * - Fires toast.success on false → true transition of orderDiscountApplied
 * - Does NOT fire when initialApplied=true (discount already active on mount)
 * - Does NOT fire on re-render when discount is unchanged (no spurious toasts)
 * - After discount is removed and re-applied, fires again (true → false → true)
 * - Toast message includes discount amount when available
 * - Toast message is generic when amount is absent
 * - Toast is sticky (duration: Infinity)
 * - Toast is dismissed when the user navigates to a different route
 * - Toast is NOT dismissed when the pathname stays the same
 */
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Module mocks ──────────────────────────────────────────────────────────────

const cartState: {
  orderDiscountApplied: boolean;
  orderDiscountAmount: string | null;
  refreshCart: ReturnType<typeof vi.fn>;
  count: number;
  resetCount: ReturnType<typeof vi.fn>;
} = {
  orderDiscountApplied: false,
  orderDiscountAmount: null,
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
  currentPathname = "/products";
  mockToastSuccess.mockClear();
  mockToastDismiss.mockClear();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useOrderDiscountToast", () => {
  describe("toast on false → true transition", () => {
    it("fires toast.success when orderDiscountApplied transitions from false to true", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast(false));

      expect(mockToastSuccess).not.toHaveBeenCalled();

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();

      expect(mockToastSuccess).toHaveBeenCalledOnce();
    });

    it("toast message contains 'Good news'", () => {
      renderHook(() => useOrderDiscountToast(false));

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      // re-render is implicit via act + state update in renderHook context
      renderHook(() => useOrderDiscountToast(false));

      // Ensure the first call's message starts with "Good news"
      const calls = mockToastSuccess.mock.calls;
      const message = calls[calls.length - 1]?.[0] as string;
      expect(message).toMatch(/good news/i);
    });

    it("includes the discount amount in the message when amount is > 0", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast(false));

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
      const { rerender } = renderHook(() => useOrderDiscountToast(false));

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();

      const message = mockToastSuccess.mock.calls[0]?.[0] as string;
      expect(message).not.toContain("null");
      expect(message).toMatch(/order discount has been applied/i);
    });

    it("toast is sticky — duration is Infinity", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast(false));

      act(() => {
        cartState.orderDiscountApplied = true;
      });
      rerender();

      const options = mockToastSuccess.mock.calls[0]?.[1] as { duration?: number };
      expect(options?.duration).toBe(Infinity);
    });
  });

  describe("no spurious toasts", () => {
    it("does NOT fire when initialApplied=true and discount is already active on mount", () => {
      cartState.orderDiscountApplied = true;
      renderHook(() => useOrderDiscountToast(true));

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });

    it("does NOT fire on subsequent re-renders when discount remains true", () => {
      cartState.orderDiscountApplied = true;
      const { rerender } = renderHook(() => useOrderDiscountToast(true));

      rerender();
      rerender();

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });

    it("does NOT fire when discount stays false across re-renders", () => {
      const { rerender } = renderHook(() => useOrderDiscountToast(false));

      rerender();
      rerender();

      expect(mockToastSuccess).not.toHaveBeenCalled();
    });
  });

  describe("re-application after removal", () => {
    it("fires again when discount is removed and then re-applied", () => {
      // Initial mount: discount active, seeded as true → no toast
      cartState.orderDiscountApplied = true;
      const { rerender } = renderHook(() => useOrderDiscountToast(true));
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

  describe("navigation dismissal", () => {
    it("dismisses the sticky toast when the user navigates to a different route", () => {
      // Fire the toast first.
      const { rerender } = renderHook(() => useOrderDiscountToast(false));
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
      const { rerender } = renderHook(() => useOrderDiscountToast(false));
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
      const { rerender } = renderHook(() => useOrderDiscountToast(false));

      act(() => {
        currentPathname = "/checkout";
      });
      rerender();

      expect(mockToastDismiss).not.toHaveBeenCalled();
    });
  });
});
