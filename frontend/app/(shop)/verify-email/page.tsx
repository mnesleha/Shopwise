"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { verifyEmail } from "@/lib/api/auth";
import { useAuth } from "@/components/auth/AuthProvider";

export default function VerifyEmailPage() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useAuth();

  const token = params.get("token");
  const [status, setStatus] = React.useState<
    "idle" | "verifying" | "success" | "error"
  >("idle");
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!token) {
        setStatus("error");
        setErrorMessage("Missing verification token.");
        return;
      }

      setStatus("verifying");
      setErrorMessage(null);

      try {
        const resp = await verifyEmail(token);
        if (cancelled) return;

        await refresh();

        toast.success("Email verified.");
        if (resp?.claimed_orders && resp.claimed_orders > 0) {
          toast.success(
            `Found ${resp.claimed_orders} guest order(s) and linked them to your account.`,
          );
        }

        setStatus("success");
        router.replace("/orders");
      } catch (e: any) {
        if (cancelled) return;

        const msg =
          e?.response?.data?.message ||
          e?.response?.data?.detail ||
          e?.message ||
          "Email verification failed.";

        setStatus("error");
        setErrorMessage(String(msg));
        toast.error("Email verification failed.");
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [token, refresh, router]);

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center px-4">
      {status === "verifying" && (
        <div className="w-full rounded-lg border p-6 text-center">
          <h1 className="text-xl font-semibold">Verifying email…</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Please wait while we confirm your email address.
          </p>
        </div>
      )}

      {status === "success" && (
        <div className="w-full rounded-lg border p-6 text-center">
          <h1 className="text-xl font-semibold">Email verified</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Redirecting you to your orders…
          </p>
        </div>
      )}

      {status === "error" && (
        <div className="w-full rounded-lg border p-6 text-center">
          <h1 className="text-xl font-semibold">Verification failed</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {errorMessage ?? "Something went wrong."}
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <button
              className="rounded-md border px-3 py-2 text-sm hover:bg-accent"
              onClick={() => router.replace("/login")}
            >
              Go to login
            </button>
            <button
              className="rounded-md border px-3 py-2 text-sm hover:bg-accent"
              onClick={() => router.replace("/orders")}
            >
              Go to orders
            </button>
          </div>
        </div>
      )}

      {status === "idle" && (
        <div className="w-full rounded-lg border p-6 text-center">
          <h1 className="text-xl font-semibold">Preparing verification…</h1>
        </div>
      )}
    </div>
  );
}
