import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createRouterMock } from "../helpers/nextNavigation";

const mockRouter = createRouterMock();
const mockLogout = vi.fn();
const mockSetAnonymous = vi.fn();
const mockResetCount = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

vi.mock("@/lib/api/auth", () => ({
  logout: (...args: unknown[]) => mockLogout(...args),
}));

vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    email: "user@example.com",
    firstName: "Test",
    lastName: "User",
    setAnonymous: mockSetAnonymous,
  }),
}));

vi.mock("@/components/cart/CartProvider", () => ({
  useCart: () => ({
    resetCount: mockResetCount,
  }),
}));

import HeaderAuthClient from "@/components/shell/HeaderAuthClient";

describe("HeaderAuthClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLogout.mockResolvedValue(undefined);
  });

  it("clears auth and cart badge on logout before navigating", async () => {
    const user = userEvent.setup();

    render(<HeaderAuthClient />);
    await user.click(screen.getByTestId("nav-logout"));

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledTimes(1);
      expect(mockSetAnonymous).toHaveBeenCalledTimes(1);
      expect(mockResetCount).toHaveBeenCalledTimes(1);
      expect(mockRouter.push).toHaveBeenCalledWith("/products");
    });
  });
});