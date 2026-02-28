"use client";

import * as React from "react";
import { toast } from "sonner";
import { requestEmailVerification } from "@/lib/api/auth";

type Props = {
  email: string;
};

export default function ResendVerificationButton({ email }: Props) {
  const [isSending, setIsSending] = React.useState(false);

  const onClick = async () => {
    setIsSending(true);
    try {
      await requestEmailVerification(email);
      toast.success("Verification email sent. Please check your inbox.");
    } catch (e: any) {
      const msg =
        e?.response?.data?.message ||
        e?.response?.data?.detail ||
        e?.message ||
        "Failed to send verification email.";
      toast.error(String(msg));
    } finally {
      setIsSending(false);
    }
  };

  return (
    <button
      className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
      onClick={onClick}
      disabled={isSending}
      type="button"
    >
      {isSending ? "Sending…" : "Resend verification email"}
    </button>
  );
}
