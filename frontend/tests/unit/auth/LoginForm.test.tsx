/**
 * LoginForm — Type A (Presentational + internal validation)
 *
 * Contract guarded:
 * - Renders form fields and submit button
 * - Displays server-side errorMessage from props
 * - Validates required fields on submit
 * - Validates email format on submit
 * - Calls onSubmit with trimmed email + password
 * - Disables submit and shows loading text while isSubmitting
 * - Renders optional "Forgot password" and "Go to register" links
 * - Toggles password visibility
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginForm from "@/components/auth/LoginForm";
import { renderWithProviders } from "../helpers/render";
import { LOGIN_FORM, LOGIN_SUBMIT } from "../helpers/testIds";

function renderForm(props: Partial<React.ComponentProps<typeof LoginForm>> = {}) {
  const onSubmit = vi.fn();
  renderWithProviders(
    <LoginForm onSubmit={onSubmit} {...props} />,
  );
  return { onSubmit };
}

describe("LoginForm", () => {
  describe("rendering", () => {
    it("renders email and password fields and submit button", () => {
      renderForm();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText("Password")).toBeInTheDocument();
      expect(screen.getByTestId(LOGIN_SUBMIT)).toBeInTheDocument();
    });

    it("renders the form container with correct testid", () => {
      renderForm();
      expect(screen.getByTestId(LOGIN_FORM)).toBeInTheDocument();
    });

    it("does NOT render forgot-password button when callback is not provided", () => {
      renderForm();
      expect(screen.queryByRole("button", { name: /forgot password/i })).toBeNull();
    });

    it("renders forgot-password button when callback is provided", () => {
      renderForm({ onForgotPassword: vi.fn() });
      expect(screen.getByRole("button", { name: /forgot password/i })).toBeInTheDocument();
    });

    it("does NOT render register link when callback is not provided", () => {
      renderForm();
      expect(screen.queryByRole("button", { name: /create one/i })).toBeNull();
    });

    it("renders register link when callback is provided", () => {
      renderForm({ onGoToRegister: vi.fn() });
      expect(screen.getByRole("button", { name: /create one/i })).toBeInTheDocument();
    });
  });

  describe("error message", () => {
    it("shows server-level error message from props", () => {
      renderForm({ errorMessage: "Invalid credentials." });
      expect(screen.getByText("Invalid credentials.")).toBeInTheDocument();
    });

    it("does not show error section when errorMessage is not provided", () => {
      renderForm();
      expect(screen.queryByText("Invalid credentials.")).toBeNull();
    });
  });

  describe("submission state", () => {
    it("shows 'Sign in' label when idle", () => {
      renderForm({ isSubmitting: false });
      expect(screen.getByTestId(LOGIN_SUBMIT)).toHaveTextContent("Sign in");
    });

    it("shows 'Signing in...' and disables the button while submitting", () => {
      renderForm({ isSubmitting: true });
      const btn = screen.getByTestId(LOGIN_SUBMIT);
      expect(btn).toBeDisabled();
      expect(btn).toHaveTextContent("Signing in...");
    });
  });

  describe("form validation", () => {
    it("shows 'Email is required' when submitting empty form", async () => {
      const user = userEvent.setup();
      renderForm();
      await user.click(screen.getByTestId(LOGIN_SUBMIT));
      expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    });

    it("shows 'valid email' error when email format is invalid", async () => {
      const user = userEvent.setup();
      renderForm();
      await user.type(screen.getByLabelText(/email/i), "not-an-email");
      await user.click(screen.getByTestId(LOGIN_SUBMIT));
      expect(await screen.findByText(/valid email/i)).toBeInTheDocument();
    });

    it("shows 'Password is required' when password is empty", async () => {
      const user = userEvent.setup();
      renderForm();
      await user.type(screen.getByLabelText(/email/i), "user@example.com");
      await user.click(screen.getByTestId(LOGIN_SUBMIT));
      expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
    });

    it("does NOT call onSubmit when validation fails", async () => {
      const user = userEvent.setup();
      const { onSubmit } = renderForm();
      await user.click(screen.getByTestId(LOGIN_SUBMIT));
      expect(onSubmit).not.toHaveBeenCalled();
    });
  });

  describe("successful submission", () => {
    it("calls onSubmit with trimmed email and password", async () => {
      const user = userEvent.setup();
      const { onSubmit } = renderForm();
      await user.type(screen.getByLabelText(/email/i), "  user@example.com  ");
      await user.type(screen.getByLabelText("Password"), "secret123");
      await user.click(screen.getByTestId(LOGIN_SUBMIT));
      await waitFor(() =>
        expect(onSubmit).toHaveBeenCalledWith({
          email: "user@example.com",
          password: "secret123",
        }),
      );
    });
  });

  describe("password visibility toggle", () => {
    it("toggles password field type between 'password' and 'text'", async () => {
      const user = userEvent.setup();
      renderForm();
      const input = screen.getByLabelText("Password");
      expect(input).toHaveAttribute("type", "password");
      await user.click(screen.getByRole("button", { name: /show password/i }));
      expect(input).toHaveAttribute("type", "text");
      await user.click(screen.getByRole("button", { name: /hide password/i }));
      expect(input).toHaveAttribute("type", "password");
    });
  });

  describe("optional callbacks", () => {
    it("calls onForgotPassword when the link is clicked", async () => {
      const user = userEvent.setup();
      const onForgotPassword = vi.fn();
      renderForm({ onForgotPassword });
      await user.click(screen.getByRole("button", { name: /forgot password/i }));
      expect(onForgotPassword).toHaveBeenCalledTimes(1);
    });

    it("calls onGoToRegister when the link is clicked", async () => {
      const user = userEvent.setup();
      const onGoToRegister = vi.fn();
      renderForm({ onGoToRegister });
      await user.click(screen.getByRole("button", { name: /create one/i }));
      expect(onGoToRegister).toHaveBeenCalledTimes(1);
    });
  });
});
