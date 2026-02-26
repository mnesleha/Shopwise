/**
 * CheckoutForm — Type A (Presentational, multi-step, internal validation)
 *
 * Contract guarded:
 * - Renders Step 1 (Shipping & Payment) by default
 * - Continue button advances to Step 2
 * - Back button on Step 2 returns to Step 1
 * - "Back to cart" button on Step 1 calls onBackToCart
 * - Step 2 renders customer details fields
 * - Submitting with empty Step 2 shows validation errors
 * - Submitting valid values calls onSubmit with the full values object
 * - initialValues pre-populate form fields
 */
import { describe, it, expect, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckoutForm } from "@/components/checkout/CheckoutForm";
import { renderWithProviders } from "../helpers/render";
import { CHECKOUT_CONTINUE, CHECKOUT_SUBMIT } from "../helpers/testIds";

function renderForm(
  props: Partial<React.ComponentProps<typeof CheckoutForm>> = {},
) {
  const onSubmit = vi.fn();
  const onBackToCart = vi.fn();
  renderWithProviders(
    <CheckoutForm onSubmit={onSubmit} onBackToCart={onBackToCart} {...props} />,
  );
  return { onSubmit, onBackToCart };
}

// Filled initialValues covering all required Step 2 fields
const VALID_STEP2: Partial<React.ComponentProps<typeof CheckoutForm>["initialValues"]> = {
  customer_email: "buyer@example.com",
  shipping_name: "Jane Doe",
  shipping_address_line1: "Test Street 1",
  shipping_city: "Prague",
  shipping_postal_code: "11000",
  shipping_country: "CZ",
  shipping_phone: "+420700000000",
  billing_same_as_shipping: true,
};

describe("CheckoutForm", () => {
  describe("step 1 rendering", () => {
    it("renders shipping method options on first load", () => {
      renderForm();
      expect(screen.getByRole("radio", { name: /standard/i })).toBeInTheDocument();
    });

    it("renders payment method options on first load", () => {
      renderForm();
      expect(screen.getByRole("radio", { name: /card/i })).toBeInTheDocument();
    });

    it("renders the Continue button", () => {
      renderForm();
      expect(screen.getByTestId(CHECKOUT_CONTINUE)).toBeInTheDocument();
    });

    it("calls onBackToCart when 'Back to cart' is clicked", async () => {
      const user = userEvent.setup();
      const { onBackToCart } = renderForm();
      await user.click(screen.getByRole("button", { name: /back to cart/i }));
      expect(onBackToCart).toHaveBeenCalledTimes(1);
    });
  });

  describe("step navigation", () => {
    it("advances to Step 2 when Continue is clicked", async () => {
      const user = userEvent.setup();
      renderForm();
      await user.click(screen.getByTestId(CHECKOUT_CONTINUE));
      // Step 2 specific element
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByTestId(CHECKOUT_SUBMIT)).toBeInTheDocument();
    });

    it("returns to Step 1 when Back is clicked on Step 2", async () => {
      const user = userEvent.setup();
      renderForm();
      await user.click(screen.getByTestId(CHECKOUT_CONTINUE));
      await user.click(screen.getByRole("button", { name: /^back$/i }));
      expect(screen.getByTestId(CHECKOUT_CONTINUE)).toBeInTheDocument();
    });
  });

  describe("step 2 validation", () => {
    async function goToStep2() {
      const user = userEvent.setup();
      const result = renderForm();
      await user.click(screen.getByTestId(CHECKOUT_CONTINUE));
      return { user, ...result };
    }

    it("shows 'Email is required' when email is empty on submit", async () => {
      const { user } = await goToStep2();
      await user.click(screen.getByTestId(CHECKOUT_SUBMIT));
      expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    });

    it("shows 'Name is required' when shipping name is empty on submit", async () => {
      const { user } = await goToStep2();
      await user.type(screen.getByLabelText(/email/i), "buyer@example.com");
      await user.click(screen.getByTestId(CHECKOUT_SUBMIT));
      expect(await screen.findByText(/name is required/i)).toBeInTheDocument();
    });

    it("shows 'valid email' error for malformed email", async () => {
      const { user } = await goToStep2();
      await user.type(screen.getByLabelText(/email/i), "not-an-email");
      await user.click(screen.getByTestId(CHECKOUT_SUBMIT));
      expect(await screen.findByText(/valid email/i)).toBeInTheDocument();
    });

    it("does NOT call onSubmit when validation fails", async () => {
      const { user, onSubmit } = await goToStep2();
      await user.click(screen.getByTestId(CHECKOUT_SUBMIT));
      expect(onSubmit).not.toHaveBeenCalled();
    });
  });

  describe("successful submission", () => {
    it("calls onSubmit with the correct values when all fields are filled", async () => {
      const user = userEvent.setup();
      const { onSubmit } = renderForm({ initialValues: VALID_STEP2 });
      await user.click(screen.getByTestId(CHECKOUT_CONTINUE));
      await user.click(screen.getByTestId(CHECKOUT_SUBMIT));
      await waitFor(() =>
        expect(onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            customer_email: "buyer@example.com",
            shipping_name: "Jane Doe",
            shipping_city: "Prague",
          }),
        ),
      );
    });
  });

  describe("initialValues", () => {
    it("pre-populates the email field from initialValues", async () => {
      const user = userEvent.setup();
      renderForm({ initialValues: { customer_email: "prefilled@example.com" } });
      await user.click(screen.getByTestId(CHECKOUT_CONTINUE));
      expect(screen.getByDisplayValue("prefilled@example.com")).toBeInTheDocument();
    });
  });
});
