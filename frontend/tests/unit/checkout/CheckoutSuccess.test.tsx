/**
 * CheckoutSuccess — Type A (Presentational)
 *
 * Contract guarded:
 * - Renders the success heading
 * - Renders the component container with the correct testid
 * - Shows the customer email when provided
 * - Does NOT show email section when customerEmail is not provided
 * - Calls onContinueShopping when the button is clicked
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckoutSuccess } from "@/components/checkout/CheckoutSuccess";
import { renderWithProviders } from "../helpers/render";
import { GUEST_CHECKOUT_SUCCESS } from "../helpers/testIds";

describe("CheckoutSuccess", () => {
  describe("rendering", () => {
    it("renders the success container with correct testid", () => {
      renderWithProviders(
        <CheckoutSuccess onContinueShopping={vi.fn()} />,
      );
      expect(screen.getByTestId(GUEST_CHECKOUT_SUCCESS)).toBeInTheDocument();
    });

    it("renders the 'Order Created Successfully' heading", () => {
      renderWithProviders(
        <CheckoutSuccess onContinueShopping={vi.fn()} />,
      );
      expect(
        screen.getByRole("heading", { name: /order created successfully/i }),
      ).toBeInTheDocument();
    });

    it("renders the 'Continue shopping' button", () => {
      renderWithProviders(
        <CheckoutSuccess onContinueShopping={vi.fn()} />,
      );
      expect(
        screen.getByRole("button", { name: /continue shopping/i }),
      ).toBeInTheDocument();
    });
  });

  describe("customer email", () => {
    it("shows the customer email when provided", () => {
      renderWithProviders(
        <CheckoutSuccess
          customerEmail="guest@example.com"
          onContinueShopping={vi.fn()}
        />,
      );
      expect(screen.getByText("guest@example.com")).toBeInTheDocument();
    });

    it("does NOT show an email address when customerEmail is not provided", () => {
      renderWithProviders(
        <CheckoutSuccess onContinueShopping={vi.fn()} />,
      );
      expect(screen.queryByText(/@/)).toBeNull();
    });
  });

  describe("callback", () => {
    it("calls onContinueShopping when the button is clicked", async () => {
      const user = userEvent.setup();
      const onContinueShopping = vi.fn();
      renderWithProviders(
        <CheckoutSuccess onContinueShopping={onContinueShopping} />,
      );
      await user.click(screen.getByRole("button", { name: /continue shopping/i }));
      expect(onContinueShopping).toHaveBeenCalledTimes(1);
    });
  });
});
