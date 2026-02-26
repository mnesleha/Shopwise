/**
 * OrderDetailClient — Type B (Client adapter)
 *
 * Contract guarded:
 * - Clicking "Back to shop" calls router.push("/products")
 * - Clicking "Print" calls window.print()
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OrderDetailClient from "@/components/order/OrderDetailClient";
import { renderWithProviders } from "../helpers/render";
import { makeOrderViewModel } from "../helpers/fixtures";
import { createRouterMock } from "../helpers/nextNavigation";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("OrderDetailClient", () => {
  it("navigates to /products when 'Back to shop' is clicked", async () => {
    const user = userEvent.setup();
    vi.clearAllMocks();
    renderWithProviders(<OrderDetailClient order={makeOrderViewModel()} />);
    const buttons = screen.getAllByRole("button", { name: /back to shop/i });
    await user.click(buttons[0]);
    expect(mockRouter.push).toHaveBeenCalledWith("/products");
  });

  it("calls window.print() when the Print button is clicked", async () => {
    const user = userEvent.setup();
    vi.clearAllMocks();
    const printSpy = vi.spyOn(window, "print").mockImplementation(() => {});
    renderWithProviders(<OrderDetailClient order={makeOrderViewModel()} />);
    await user.click(screen.getByRole("button", { name: /print/i }));
    expect(printSpy).toHaveBeenCalledTimes(1);
    printSpy.mockRestore();
  });
});
