/**
 * LoginPage — post-login side-effect toasts
 *
 * Contracts guarded:
 * 1. MERGED cart report → single success toast with merge message
 * 2. STOCK_ADJUSTED warning → sticky warning toast shown once
 * 3. claimed_orders > 0 → single success toast with claim count
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../helpers/render";
import { createRouterMock } from "../helpers/nextNavigation";
import LoginPage from "@/app/(shop)/login/page";
import { LOGIN_SUBMIT } from "../helpers/testIds";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => new URLSearchParams(),
}));

const mockLogin = vi.fn();
const mockMergeCart = vi.fn();
const mockClaimOrders = vi.fn();

vi.mock("@/lib/api/auth", () => ({
  login: (...args: unknown[]) => mockLogin(...args),
}));

vi.mock("@/lib/api/cart", () => ({
  mergeCart: (...args: unknown[]) => mockMergeCart(...args),
}));

vi.mock("@/lib/api/orders", () => ({
  claimOrders: (...args: unknown[]) => mockClaimOrders(...args),
}));

const mockRefresh = vi.fn();
const mockRefreshCart = vi.fn();

vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => ({ refresh: mockRefresh }),
}));

vi.mock("@/components/cart/CartProvider", () => ({
  useCart: () => ({ refreshCart: mockRefreshCart, count: 0 }),
}));

const mockToastSuccess = vi.fn();
const mockToastWarning = vi.fn();
const mockToastDismiss = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    warning: (...args: unknown[]) => mockToastWarning(...args),
    error: vi.fn(),
    dismiss: (...args: unknown[]) => mockToastDismiss(...args),
  },
}));

// ── helpers ───────────────────────────────────────────────────────────────────

function makeNoopReport() {
  return {
    performed: false,
    result: "NOOP" as const,
    items_added: 0,
    items_updated: 0,
    items_removed: 0,
    warnings: [],
  };
}

async function fillAndSubmit() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/email/i), "user@example.com");
  await user.type(screen.getByLabelText("Password"), "P@ssw0rd");
  await user.click(screen.getByTestId(LOGIN_SUBMIT));
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe("LoginPage — post-login toasts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    mockLogin.mockResolvedValue({ access: "tok" });
    mockRefresh.mockResolvedValue(undefined);
    mockRefreshCart.mockResolvedValue(undefined);
    mockMergeCart.mockResolvedValue(makeNoopReport());
    mockClaimOrders.mockResolvedValue({ claimed_orders: 0 });
  });

  it("shows a success toast when cart was MERGED", async () => {
    mockMergeCart.mockResolvedValue({
      performed: true,
      result: "MERGED",
      items_added: 0,
      items_updated: 1,
      items_removed: 0,
      warnings: [],
    });

    renderWithProviders(<LoginPage />);
    await fillAndSubmit();

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith("We synced your carts.");
    });
    expect(mockToastSuccess).toHaveBeenCalledTimes(1);
    expect(mockToastWarning).not.toHaveBeenCalled();
  });

  it("shows a success toast when cart was ADOPTED", async () => {
    mockMergeCart.mockResolvedValue({
      performed: true,
      result: "ADOPTED",
      items_added: 2,
      items_updated: 0,
      items_removed: 0,
      warnings: [],
    });

    renderWithProviders(<LoginPage />);
    await fillAndSubmit();

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "We restored your saved cart.",
      );
    });
    expect(mockToastSuccess).toHaveBeenCalledTimes(1);
  });

  it("shows a sticky warning toast when STOCK_ADJUSTED warning is present", async () => {
    const warnings = [
      { code: "STOCK_ADJUSTED", product_id: 5, requested: 10, applied: 3 },
    ];
    mockMergeCart.mockResolvedValue({
      performed: true,
      result: "MERGED",
      items_added: 0,
      items_updated: 1,
      items_removed: 0,
      warnings,
    });

    renderWithProviders(<LoginPage />);
    await fillAndSubmit();

    await waitFor(() => {
      expect(mockToastWarning).toHaveBeenCalledWith(
        "Some item quantities were adjusted due to stock availability.",
        expect.objectContaining({
          duration: Infinity,
          action: expect.objectContaining({ label: "Review adjustments" }),
        }),
      );
    });
    expect(mockToastWarning).toHaveBeenCalledTimes(1);
  });

  it("persists warnings to sessionStorage when STOCK_ADJUSTED is present", async () => {
    const warnings = [
      { code: "STOCK_ADJUSTED", product_id: 5, requested: 10, applied: 3 },
    ];
    mockMergeCart.mockResolvedValue({
      performed: true,
      result: "MERGED",
      items_added: 0,
      items_updated: 1,
      items_removed: 0,
      warnings,
    });

    renderWithProviders(<LoginPage />);
    await fillAndSubmit();

    await waitFor(() => {
      expect(sessionStorage.getItem("cartMergeWarnings")).toBe(
        JSON.stringify(warnings),
      );
    });
  });

  it("does not write to sessionStorage when there are no warnings", async () => {
    // defaults: NOOP merge, 0 claimed_orders
    renderWithProviders(<LoginPage />);
    await fillAndSubmit();

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith("/products");
    });
    expect(sessionStorage.getItem("cartMergeWarnings")).toBeNull();
  });

  it("shows a claimed-orders success toast when claimed_orders > 0", async () => {
    mockClaimOrders.mockResolvedValue({ claimed_orders: 3 });

    renderWithProviders(<LoginPage />);
    await fillAndSubmit();

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "We found 3 guest order(s) and linked them to your account.",
      );
    });
  });

  it("shows no toast when result is NOOP and no warnings", async () => {
    // defaults: NOOP merge, 0 claimed_orders
    renderWithProviders(<LoginPage />);
    await fillAndSubmit();

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith("/products");
    });
    expect(mockToastSuccess).not.toHaveBeenCalled();
    expect(mockToastWarning).not.toHaveBeenCalled();
  });
});
