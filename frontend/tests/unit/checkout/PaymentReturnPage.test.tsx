/**
 * PaymentReturnPage — branching / UX tests
 *
 * Contract guarded:
 * - no context in storage              → no_context state rendered
 * - guest context                      → guest_success state rendered
 * - auth, order status CREATED         → pending state rendered
 * - auth, order status PAID            → paid state, then navigates to order
 * - auth, order status PAYMENT_FAILED  → failed state rendered
 * - auth, getOrder throws              → pending state (fail-safe)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PaymentReturnPageClient from "@/components/checkout/PaymentReturnPageClient";
import type { BaseOrderDto } from "@/lib/api/orders";
import type { PaymentReturnContext } from "@/lib/utils/paymentReturn";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const mockGetOrder = vi.fn();

vi.mock("@/lib/api/orders", () => ({
  getOrder: (...args: unknown[]) => mockGetOrder(...args),
}));

const mockLoadAndClear = vi.fn<() => PaymentReturnContext | null>();
const mockLoadFromSearchParams =
  vi.fn<(searchParams: URLSearchParams) => PaymentReturnContext | null>();

vi.mock("@/lib/utils/paymentReturn", () => ({
  loadAndClearPaymentReturnContext: () => mockLoadAndClear(),
  loadPaymentReturnContextFromSearchParams: (...args: [URLSearchParams]) =>
    mockLoadFromSearchParams(...args),
  savePaymentReturnContext: vi.fn(),
}));

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeOrderDto(status: string): BaseOrderDto {
  return {
    id: 42,
    status,
    created_at: null,
    items: [],
    total: "100.00",
    subtotal_net: null,
    subtotal_gross: null,
    total_tax: null,
    total_discount: null,
    currency: "USD",
    vat_breakdown: null,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PaymentReturnPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetOrder.mockReset();
    mockLoadAndClear.mockReset();
    mockLoadFromSearchParams.mockReset();
    mockRouter.push.mockReset();
    mockRouter.replace.mockReset();
    mockRouter.back.mockReset();
    mockRouter.forward.mockReset();
    mockRouter.refresh.mockReset();
    mockRouter.prefetch.mockReset();
    mockLoadFromSearchParams.mockReturnValue(null);
  });

  it("shows no-context state when sessionStorage has no payment context", async () => {
    mockLoadAndClear.mockReturnValue(null);

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(
        screen.getByTestId("payment-return-no-context"),
      ).toBeInTheDocument();
    });
    expect(mockGetOrder).not.toHaveBeenCalled();
  });

  it("falls back to URL params when storage context is missing", async () => {
    mockLoadAndClear.mockReturnValue(null);
    mockLoadFromSearchParams.mockReturnValue({ orderId: 42, isGuest: false });
    mockGetOrder.mockResolvedValue(makeOrderDto("PAID"));

    render(
      <PaymentReturnPageClient initialOrderId="42" initialGuest="false" />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-paid")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith("/orders/42");
    });
  });

  it("shows guest success state for a guest checkout context", async () => {
    mockLoadAndClear.mockReturnValue({ orderId: 7, isGuest: true });

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(
        screen.getByTestId("payment-return-guest-success"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Check your email")).toBeInTheDocument();
    expect(
      screen.getByText(/We sent an order access link to your email/i),
    ).toBeInTheDocument();
    expect(mockGetOrder).not.toHaveBeenCalled();
  });

  it("shows pending state when order status is CREATED", async () => {
    mockLoadAndClear.mockReturnValue({ orderId: 42, isGuest: false });
    mockGetOrder.mockResolvedValue(makeOrderDto("CREATED"));

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-pending")).toBeInTheDocument();
    });
    expect(mockGetOrder).toHaveBeenCalledWith(42);
  });

  it("shows paid state and navigates to order when order status is PAID", async () => {
    mockLoadAndClear.mockReturnValue({ orderId: 42, isGuest: false });
    mockGetOrder.mockResolvedValue(makeOrderDto("PAID"));

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-paid")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith("/orders/42");
    });
  });

  it("shows failed state when order status is PAYMENT_FAILED", async () => {
    mockLoadAndClear.mockReturnValue({ orderId: 42, isGuest: false });
    mockGetOrder.mockResolvedValue(makeOrderDto("PAYMENT_FAILED"));

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-failed")).toBeInTheDocument();
    });
    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  it("shows pending state (fail-safe) when getOrder throws", async () => {
    mockLoadAndClear.mockReturnValue({ orderId: 42, isGuest: false });
    mockGetOrder.mockRejectedValue(new Error("network error"));

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-pending")).toBeInTheDocument();
    });
  });

  it("does not navigate for failed state", async () => {
    mockLoadAndClear.mockReturnValue({ orderId: 42, isGuest: false });
    mockGetOrder.mockResolvedValue(makeOrderDto("PAYMENT_FAILED"));

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-failed")).toBeInTheDocument();
    });
    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  it("back-to-cart button navigates to /cart from failed state", async () => {
    const user = userEvent.setup();
    mockLoadAndClear.mockReturnValue({ orderId: 42, isGuest: false });
    mockGetOrder.mockResolvedValue(makeOrderDto("PAYMENT_FAILED"));

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-failed")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("payment-return-back-to-cart"));
    expect(mockRouter.push).toHaveBeenCalledWith("/cart");
  });

  it("check-again button re-fetches order status from pending state", async () => {
    const user = userEvent.setup();
    mockLoadAndClear.mockReturnValue({ orderId: 42, isGuest: false });
    // First call → pending; second call (check again) → paid
    mockGetOrder
      .mockResolvedValueOnce(makeOrderDto("CREATED"))
      .mockResolvedValueOnce(makeOrderDto("PAID"));

    render(<PaymentReturnPageClient />);

    await waitFor(() => {
      expect(screen.getByTestId("payment-return-pending")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("payment-return-check-again"));

    await waitFor(() => {
      expect(mockGetOrder).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith("/orders/42");
    });
  });
});
