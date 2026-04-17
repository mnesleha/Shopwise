/**
 * ClaimOfferClient — Phase 4 / Slice 5B
 *
 * Contract guarded:
 * - Shows loading state while the claim request is in flight
 * - Shows "Campaign offer applied" with promotion name on success
 * - Shows "Go to cart" CTA on success
 * - Calls refreshCart() after a successful claim
 * - Cleans the URL (router.replace "/claim-offer") after success
 * - Shows error state with specific message when no token is in the URL
 * - Shows error state when the API returns any error
 * - Uses the error message from the API response body when available
 * - Shows "Continue shopping" CTA on error
 * - Cleans the URL even when the claim fails
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ClaimOfferClient from "@/app/(shop)/claim-offer/ClaimOfferClient";
import { renderWithProviders } from "../helpers/render";
import { createRouterMock } from "../helpers/nextNavigation";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/claim-offer",
}));

const mockClaimCampaignOffer = vi.fn();

vi.mock("@/lib/api/cart", () => ({
  claimCampaignOffer: (...args: unknown[]) => mockClaimCampaignOffer(...args),
}));

const mockRefreshCart = vi.fn();

vi.mock("@/components/cart/CartProvider", () => ({
  useCart: () => ({ refreshCart: mockRefreshCart }),
}));

// ── Constants ─────────────────────────────────────────────────────────────────

const TEST_TOKEN = "test-campaign-token-abc";

const SUCCESS_RESPONSE = {
  promotion_name: "Summer Sale",
  promotion_code: "SUMMER10",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderClient(token: string | null = TEST_TOKEN) {
  return renderWithProviders(<ClaimOfferClient token={token} />);
}

// ── Test suite ────────────────────────────────────────────────────────────────

describe("ClaimOfferClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default: claim API succeeds.
    mockClaimCampaignOffer.mockResolvedValue(SUCCESS_RESPONSE);

    // Default: refreshCart resolves immediately.
    mockRefreshCart.mockResolvedValue(undefined);
  });

  // ── Loading state ────────────────────────────────────────────────────────

  it("shows loading state while the claim request is in flight", () => {
    // Suspend the claim so we can assert against the intermediate render.
    mockClaimCampaignOffer.mockImplementation(
      () =>
        new Promise(() => {
          /* intentionally never resolves */
        }),
    );

    renderClient();

    expect(screen.getByText("Applying your offer…")).toBeInTheDocument();
  });

  // ── Success path ─────────────────────────────────────────────────────────

  it("shows 'Campaign offer applied' heading on success", async () => {
    renderClient();

    await waitFor(() => {
      expect(screen.getByTestId("claim-offer-success")).toBeInTheDocument();
    });

    expect(
      screen.getByRole("heading", { name: /campaign offer applied/i }),
    ).toBeInTheDocument();
  });

  it("displays the promotion name returned by the API", async () => {
    renderClient();

    await waitFor(() => {
      expect(screen.getByTestId("claim-offer-success")).toBeInTheDocument();
    });

    expect(screen.getByText(/Summer Sale/)).toBeInTheDocument();
  });

  it("shows a 'Go to cart' button on success", async () => {
    renderClient();

    await waitFor(() => {
      expect(screen.getByTestId("go-to-cart")).toBeInTheDocument();
    });
  });

  it("navigates to /cart when 'Go to cart' is clicked", async () => {
    const user = userEvent.setup();
    renderClient();

    await waitFor(() => {
      expect(screen.getByTestId("go-to-cart")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("go-to-cart"));

    expect(mockRouter.push).toHaveBeenCalledWith("/cart");
  });

  it("calls refreshCart() once after a successful claim", async () => {
    renderClient();

    await waitFor(() => {
      expect(mockRefreshCart).toHaveBeenCalledTimes(1);
    });
  });

  it("cleans the URL after a successful claim", async () => {
    renderClient();

    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalledWith("/claim-offer");
    });
  });

  // ── Error path: missing token ─────────────────────────────────────────────

  it("shows an error when no token is present in the URL", async () => {
    renderClient(null);

    await waitFor(() => {
      expect(screen.getByTestId("claim-offer-error")).toBeInTheDocument();
    });

    expect(
      screen.getByText("No offer token found in the link."),
    ).toBeInTheDocument();
  });

  it("does not call the claim API when no token is present", async () => {
    renderClient(null);

    await waitFor(() => {
      expect(screen.getByTestId("claim-offer-error")).toBeInTheDocument();
    });

    expect(mockClaimCampaignOffer).not.toHaveBeenCalled();
  });

  // ── Error path: API failure ───────────────────────────────────────────────

  it("shows an error state when the API returns an error", async () => {
    mockClaimCampaignOffer.mockRejectedValue(new Error("Network error"));

    renderClient();

    await waitFor(() => {
      expect(screen.getByTestId("claim-offer-error")).toBeInTheDocument();
    });
  });

  it("displays the error message from the API response body", async () => {
    const apiError = {
      response: {
        data: { message: "Offer has expired.", code: "OFFER_INACTIVE" },
      },
    };
    mockClaimCampaignOffer.mockRejectedValue(apiError);

    renderClient();

    await waitFor(() => {
      expect(screen.getByText("Offer has expired.")).toBeInTheDocument();
    });
  });

  it("falls back to a generic message when the API error has no body", async () => {
    mockClaimCampaignOffer.mockRejectedValue(new Error("unknown"));

    renderClient();

    await waitFor(() => {
      expect(
        screen.getByText("This offer is no longer available."),
      ).toBeInTheDocument();
    });
  });

  it("shows a 'Continue shopping' button on error", async () => {
    mockClaimCampaignOffer.mockRejectedValue(new Error("fail"));

    renderClient();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /continue shopping/i }),
      ).toBeInTheDocument();
    });
  });

  it("cleans the URL even when the claim fails", async () => {
    mockClaimCampaignOffer.mockRejectedValue(new Error("fail"));

    renderClient();

    await waitFor(() => {
      expect(mockRouter.replace).toHaveBeenCalledWith("/claim-offer");
    });
  });
});
