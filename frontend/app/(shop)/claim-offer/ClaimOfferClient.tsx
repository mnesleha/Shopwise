"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { claimCampaignOffer } from "@/lib/api/cart";
import { useCart } from "@/components/cart/CartProvider";

type ClaimStatus = "idle" | "claiming" | "success" | "error";
type ClaimOfferClientProps = {
  token: string | null;
};

/**
 * Phase 4 / Slice 5B — Campaign offer claim client component.
 *
 * Reads the `token` query parameter, calls the backend claim endpoint,
 * refreshes the cart, and presents the result.  The token is removed from
 * the URL after processing so it does not linger in browser history.
 */
export default function ClaimOfferClient({ token }: ClaimOfferClientProps) {
  const router = useRouter();
  const { refreshCart } = useCart();

  const [claimStatus, setClaimStatus] = React.useState<ClaimStatus>("idle");
  const [promotionName, setPromotionName] = React.useState<string | null>(null);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!token) {
        setClaimStatus("error");
        setErrorMessage("No offer token found in the link.");
        return;
      }

      setClaimStatus("claiming");

      try {
        const result = await claimCampaignOffer(token);
        if (cancelled) return;

        setPromotionName(result.promotion_name);
        setClaimStatus("success");

        // Refresh cart so the applied discount is immediately visible.
        await refreshCart();

        // Clean the URL: remove the token query parameter.
        router.replace("/claim-offer");
      } catch (err: unknown) {
        if (cancelled) return;

        const anyErr = err as {
          response?: { data?: { message?: string; code?: string } };
        };
        const msg =
          anyErr?.response?.data?.message ??
          "This offer is no longer available.";
        setErrorMessage(msg);
        setClaimStatus("error");

        // Clean URL even on failure so the token does not stay in the address bar.
        router.replace("/claim-offer");
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
    // Run once on mount — token comes from the initial URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center px-4">
      {(claimStatus === "idle" || claimStatus === "claiming") && (
        <div className="w-full rounded-lg border p-6 text-center">
          <h1 className="text-xl font-semibold">Applying your offer…</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Please wait while we apply your exclusive offer.
          </p>
        </div>
      )}

      {claimStatus === "success" && (
        <div
          className="w-full rounded-lg border p-6 text-center"
          data-testid="claim-offer-success"
        >
          <h1 className="text-xl font-semibold text-emerald-600 dark:text-emerald-400">
            Campaign offer applied
          </h1>
          {promotionName && (
            <p className="mt-2 text-sm text-muted-foreground">
              <span className="font-medium">{promotionName}</span> has been
              added to your cart.
            </p>
          )}
          <p className="mt-1 text-sm text-muted-foreground">
            Your offer has been applied. Head to your cart to see the updated
            total.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <button
              data-testid="go-to-cart"
              className="rounded-md border px-3 py-2 text-sm hover:bg-accent"
              onClick={() => router.push("/cart")}
            >
              Go to cart
            </button>
            <button
              className="rounded-md border px-3 py-2 text-sm hover:bg-accent"
              onClick={() => router.push("/products")}
            >
              Continue shopping
            </button>
          </div>
        </div>
      )}

      {claimStatus === "error" && (
        <div
          className="w-full rounded-lg border p-6 text-center"
          data-testid="claim-offer-error"
        >
          <h1 className="text-xl font-semibold">Offer not available</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {errorMessage ?? "This offer is no longer available."}
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <button
              className="rounded-md border px-3 py-2 text-sm hover:bg-accent"
              onClick={() => router.push("/products")}
            >
              Continue shopping
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
