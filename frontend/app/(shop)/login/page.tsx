"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import LoginForm from "@/components/auth/LoginForm";
import { login } from "@/lib/api/auth";
import { setTokens } from "@/lib/auth/tokens";
import { useAuth } from "@/components/auth/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(
    undefined,
  );

  const onSubmit = async (values: { email: string; password: string }) => {
    setIsSubmitting(true);
    setErrorMessage(undefined);

    try {
      await login(values);
      await refresh(); // updates AuthProvider context — HeaderAuthClient reacts instantly

      // MVP redirect: back to products (later you can redirect to /orders)
      router.push("/products");
    } catch (e: any) {
      // backend might return {code,message} or DRF-like detail – keep robust
      const msg =
        e?.response?.data?.message ||
        e?.response?.data?.detail ||
        e?.message ||
        "Login failed";
      setErrorMessage(String(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md py-10">
      <LoginForm
        onSubmit={onSubmit}
        isSubmitting={isSubmitting}
        errorMessage={errorMessage}
      />
    </div>
  );
}
