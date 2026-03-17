import * as React from "react";
import ClaimOfferClient from "./ClaimOfferClient";

export const metadata = {
  title: "Claim Offer | Shopwise",
};

/**
 * Phase 4 / Slice 5B — /claim-offer route.
 *
 * Wraps ``ClaimOfferClient`` in ``Suspense`` as required by Next.js when
 * ``useSearchParams`` is used inside a client component.
 */
export default function ClaimOfferPage() {
  return (
    <React.Suspense
      fallback={
        <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center px-4">
          <div className="w-full rounded-lg border p-6 text-center">
            <h1 className="text-xl font-semibold">Loading…</h1>
          </div>
        </div>
      }
    >
      <ClaimOfferClient />
    </React.Suspense>
  );
}
