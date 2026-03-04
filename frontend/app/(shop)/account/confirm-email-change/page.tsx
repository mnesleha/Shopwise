/**
 * Server Component: confirm a pending email-change request.
 *
 * Flow:
 *  1. Read `token` from searchParams.
 *  2. Call GET /api/v1/account/confirm-email-change/?token=...
 *     - 204 → redirect to /login?emailChanged=1
 *     - 4xx / missing token → render an error card with a CTA.
 */

import Link from "next/link";
import { redirect } from "next/navigation";

type Props = {
  searchParams: Promise<{ token?: string }>;
};

export default async function ConfirmEmailChangePage({ searchParams }: Props) {
  const { token } = await searchParams;

  // --- Missing token ---
  if (!token) {
    return (
      <TokenErrorCard
        heading="Invalid confirmation link"
        body="The confirmation link is missing a token. Please check your email and try again."
        cta={{ label: "Go to profile", href: "/profile" }}
      />
    );
  }

  // --- Call the backend. apiFetch is skipped here because the endpoint
  //     returns 204 (no body) and the shared helper tries to parse JSON. ---
  const baseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
  let errorMessage: string | null = null;

  try {
    const res = await fetch(
      `${baseUrl}/api/v1/account/confirm-email-change/?token=${encodeURIComponent(token)}`,
      { method: "GET", cache: "no-store" },
    );

    if (!res.ok) {
      let body: { message?: string; detail?: string; errors?: Record<string, string[]> } = {};
      try {
        body = await res.json();
      } catch {
        // ignore JSON parse failure
      }
      errorMessage =
        body.message ||
        (body.errors &&
          Object.values(body.errors).flat().join(" ")) ||
        body.detail ||
        `Request failed (${res.status}).`;
    }
  } catch {
    errorMessage = "Unable to reach the server. Please try again later.";
  }

  // Success path — redirect outside try/catch so Next.js redirect works cleanly.
  if (!errorMessage) {
    redirect("/login?emailChanged=1");
  }

  // --- Error state ---
  return (
    <TokenErrorCard
      heading="Email change failed"
      body={errorMessage}
      cta={{ label: "Go to profile", href: "/profile" }}
    />
  );
}

// ---------------------------------------------------------------------------
// Shared UI helper (file-private)
// ---------------------------------------------------------------------------

function TokenErrorCard({
  heading,
  body,
  cta,
}: {
  heading: string;
  body: string;
  cta: { label: string; href: string };
}) {
  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center px-4">
      <div className="w-full rounded-lg border p-6 text-center space-y-4">
        <h1 className="text-xl font-semibold text-destructive">{heading}</h1>
        <p className="text-sm text-muted-foreground">{body}</p>
        <Link
          href={cta.href}
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {cta.label}
        </Link>
      </div>
    </div>
  );
}
