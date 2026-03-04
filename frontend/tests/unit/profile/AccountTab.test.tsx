/**
 * AccountTab – RTL unit tests
 *
 * Contracts guarded:
 * A) Renders email and inputs for first/last name
 * B) Clicking Save triggers PATCH /api/v1/account/ with correct body + success toast
 * C) When email_verified=false, renders ResendVerificationButton
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../helpers/render";
import { createRouterMock } from "../helpers/nextNavigation";
import type { AccountDto } from "@/lib/api/profile";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/profile",
}));

const mockPatchAccount = vi.fn();
vi.mock("@/lib/api/profile", () => ({
  patchAccount: (...args: unknown[]) => mockPatchAccount(...args),
}));

const mockRefreshAuth = vi.fn();
vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => ({ refresh: mockRefreshAuth }),
}));

const mockRequestEmailVerification = vi.fn();
vi.mock("@/lib/api/auth", () => ({
  requestEmailVerification: (...args: unknown[]) =>
    mockRequestEmailVerification(...args),
}));

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeAccount(overrides?: Partial<AccountDto>): AccountDto {
  return {
    email: "user@example.com",
    first_name: "Alice",
    last_name: "Smith",
    ...overrides,
  };
}

// ── Test suite ────────────────────────────────────────────────────────────────

describe("AccountTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("A) renders email and first/last name inputs", async () => {
    const { AccountTab } = await import("@/components/profile/AccountTab");

    renderWithProviders(
      <AccountTab account={makeAccount()} emailVerified={true} />,
    );

    // Email is displayed (read-only)
    expect(screen.getByTestId("account-email")).toHaveTextContent(
      "user@example.com",
    );

    // Editable inputs pre-filled with name values
    expect(screen.getByTestId("input-first-name")).toHaveValue("Alice");
    expect(screen.getByTestId("input-last-name")).toHaveValue("Smith");
  });

  it("B) clicking Save triggers PATCH with correct body and shows success toast", async () => {
    const user = userEvent.setup();
    const { AccountTab } = await import("@/components/profile/AccountTab");

    mockPatchAccount.mockResolvedValueOnce({
      email: "user@example.com",
      first_name: "Bob",
      last_name: "Jones",
    });
    mockRefreshAuth.mockResolvedValueOnce({ isAuthenticated: true, email: "user@example.com" });

    renderWithProviders(
      <AccountTab account={makeAccount()} emailVerified={true} />,
    );

    // Change first name
    const firstInput = screen.getByTestId("input-first-name");
    await user.clear(firstInput);
    await user.type(firstInput, "Bob");

    // Change last name
    const lastInput = screen.getByTestId("input-last-name");
    await user.clear(lastInput);
    await user.type(lastInput, "Jones");

    // Submit the form
    await user.click(screen.getByTestId("save-account-btn"));

    await waitFor(() => {
      expect(mockPatchAccount).toHaveBeenCalledWith({
        first_name: "Bob",
        last_name: "Jones",
      });
    });

    expect(mockToastSuccess).toHaveBeenCalledWith("Profile updated.");
    expect(mockRefreshAuth).toHaveBeenCalled();
    expect(mockRouter.refresh).toHaveBeenCalled();
  });

  it("C) when email_verified=false, renders ResendVerificationButton", async () => {
    const { AccountTab } = await import("@/components/profile/AccountTab");

    renderWithProviders(
      <AccountTab account={makeAccount()} emailVerified={false} />,
    );

    // Unverified badge is shown
    expect(screen.getByTestId("badge-unverified")).toBeInTheDocument();

    // ResendVerificationButton is rendered (identified by its button text)
    expect(
      screen.getByRole("button", { name: /resend verification email/i }),
    ).toBeInTheDocument();
  });
});
