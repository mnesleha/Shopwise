/**
 * GuestAccountBootstrapBanner — unit tests
 *
 * Contract guarded:
 * 1. Shows create-account banner (new email, unauthenticated).
 * 2. Shows existing-account prompt (existing email, unauthenticated).
 * 3. Shows claim-order section for authenticated users.
 * 4. Password-only form is rendered (no email / name fields).
 * 5. Mismatch validation is shown inline before submit.
 * 6. Successful bootstrap calls API, refreshes auth, and redirects.
 * 7. Missing-password validation prevents submit.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GuestAccountBootstrapBanner from "@/components/order/GuestAccountBootstrapBanner";
import { renderWithProviders } from "../helpers/render";
import { createRouterMock } from "../helpers/nextNavigation";
import {
  GUEST_BOOTSTRAP_BANNER,
  GUEST_BOOTSTRAP_EXISTING_ACCOUNT,
  GUEST_BOOTSTRAP_FORM,
  GUEST_BOOTSTRAP_SUBMIT,
} from "../helpers/testIds";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();
vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

const mockRefresh = vi.fn().mockResolvedValue({ isAuthenticated: true });
const mockUseAuth = vi.fn(() => ({
  isAuthenticated: false,
  refresh: mockRefresh,
}));

vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => mockUseAuth(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

const mockBootstrap = vi.fn();
vi.mock("@/lib/api/auth", () => ({
  bootstrapGuestAccount: (...args: unknown[]) => mockBootstrap(...args),
}));

const mockApiPost = vi.fn();
vi.mock("@/lib/api", () => ({
  api: {
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderBanner(props?: {
  emailAccountExists?: boolean;
  isAuthenticated?: boolean;
}) {
  mockUseAuth.mockReturnValue({
    isAuthenticated: props?.isAuthenticated ?? false,
    refresh: mockRefresh,
  });

  renderWithProviders(
    <GuestAccountBootstrapBanner
      orderId={42}
      token="test-token"
      emailAccountExists={props?.emailAccountExists ?? false}
    />,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("GuestAccountBootstrapBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBootstrap.mockResolvedValue({
      is_authenticated: true,
      id: 1,
      email: "guest@example.com",
      first_name: "Guest",
      last_name: "User",
      role: "CUSTOMER",
      email_verified: true,
    });
    mockRefresh.mockResolvedValue({ isAuthenticated: true });
  });

  // 1. Create-account CTA shown for unauthenticated user with new email
  describe("new email, unauthenticated", () => {
    it("shows the bootstrap banner", () => {
      renderBanner({ emailAccountExists: false });
      expect(screen.getByTestId(GUEST_BOOTSTRAP_BANNER)).toBeInTheDocument();
    });

    it("does NOT show existing-account prompt", () => {
      renderBanner({ emailAccountExists: false });
      expect(screen.queryByTestId(GUEST_BOOTSTRAP_EXISTING_ACCOUNT)).toBeNull();
    });

    // 4. Password-only form — no email / name fields
    it("renders the password-only form", () => {
      renderBanner({ emailAccountExists: false });
      expect(screen.getByTestId(GUEST_BOOTSTRAP_FORM)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /create account/i }),
      ).toBeInTheDocument();
    });

    it("does NOT render an email input", () => {
      renderBanner({ emailAccountExists: false });
      expect(screen.queryByLabelText(/email/i)).toBeNull();
    });

    it("renders password and confirm-password inputs", () => {
      renderBanner({ emailAccountExists: false });
      expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    });
  });

  // 2. Existing-account prompt
  describe("existing email, unauthenticated", () => {
    it("shows existing-account prompt", () => {
      renderBanner({ emailAccountExists: true });
      expect(
        screen.getByTestId(GUEST_BOOTSTRAP_EXISTING_ACCOUNT),
      ).toBeInTheDocument();
    });

    it("does NOT show the create-account form", () => {
      renderBanner({ emailAccountExists: true });
      expect(screen.queryByTestId(GUEST_BOOTSTRAP_FORM)).toBeNull();
    });

    it("shows sign-in button", () => {
      renderBanner({ emailAccountExists: true });
      expect(
        screen.getByRole("button", { name: /sign in/i }),
      ).toBeInTheDocument();
    });
  });

  // 3. Authenticated user
  describe("authenticated user", () => {
    it("shows the claim-order section not the create-account form", () => {
      renderBanner({ isAuthenticated: true });
      expect(screen.getByTestId(GUEST_BOOTSTRAP_BANNER)).toBeInTheDocument();
      expect(screen.queryByTestId(GUEST_BOOTSTRAP_FORM)).toBeNull();
      expect(screen.queryByTestId(GUEST_BOOTSTRAP_EXISTING_ACCOUNT)).toBeNull();
      expect(
        screen.getByRole("button", { name: /link order to account/i }),
      ).toBeInTheDocument();
    });
  });

  // 5. Mismatch validation
  describe("password mismatch", () => {
    it("shows inline error when passwords do not match", async () => {
      const user = userEvent.setup();
      renderBanner({ emailAccountExists: false });

      await user.type(screen.getByLabelText(/^password/i), "abc123");
      await user.type(screen.getByLabelText(/confirm password/i), "different");
      await user.click(screen.getByTestId(GUEST_BOOTSTRAP_SUBMIT));

      expect(
        await screen.findByText(/passwords do not match/i),
      ).toBeInTheDocument();
      expect(mockBootstrap).not.toHaveBeenCalled();
    });
  });

  // 7. Missing password
  describe("missing password", () => {
    it("shows 'Password is required' when password is empty", async () => {
      const user = userEvent.setup();
      renderBanner({ emailAccountExists: false });

      await user.click(screen.getByTestId(GUEST_BOOTSTRAP_SUBMIT));

      expect(
        await screen.findByText(/password is required/i),
      ).toBeInTheDocument();
      expect(mockBootstrap).not.toHaveBeenCalled();
    });
  });

  // 6. Successful bootstrap
  describe("successful submit", () => {
    it("calls bootstrapGuestAccount with the correct args", async () => {
      const user = userEvent.setup();
      renderBanner({ emailAccountExists: false });

      await user.type(screen.getByLabelText(/^password/i), "MyPass123!");
      await user.type(screen.getByLabelText(/confirm password/i), "MyPass123!");
      await user.click(screen.getByTestId(GUEST_BOOTSTRAP_SUBMIT));

      await waitFor(() => {
        expect(mockBootstrap).toHaveBeenCalledWith(42, "test-token", {
          password: "MyPass123!",
          password_confirm: "MyPass123!",
        });
      });
    });

    it("refreshes auth state after success", async () => {
      const user = userEvent.setup();
      renderBanner({ emailAccountExists: false });

      await user.type(screen.getByLabelText(/^password/i), "MyPass123!");
      await user.type(screen.getByLabelText(/confirm password/i), "MyPass123!");
      await user.click(screen.getByTestId(GUEST_BOOTSTRAP_SUBMIT));

      await waitFor(() => {
        expect(mockRefresh).toHaveBeenCalled();
      });
    });

    it("redirects to authenticated order detail on success", async () => {
      const user = userEvent.setup();
      renderBanner({ emailAccountExists: false });

      await user.type(screen.getByLabelText(/^password/i), "MyPass123!");
      await user.type(screen.getByLabelText(/confirm password/i), "MyPass123!");
      await user.click(screen.getByTestId(GUEST_BOOTSTRAP_SUBMIT));

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith("/orders/42");
      });
    });
  });
});
