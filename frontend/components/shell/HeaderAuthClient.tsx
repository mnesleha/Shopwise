"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api/auth";
import { useAuth } from "@/components/auth/AuthProvider";

export default function HeaderAuthClient() {
  const router = useRouter();
  const { isAuthenticated, email, setAnonymous } = useAuth();

  const onLogout = async () => {
    await logout();
    setAnonymous(); // immediately clear auth context — no router.refresh() needed
    router.push("/products");
  };

  return (
    <>
      {isAuthenticated && email ? (
        <span data-testid="auth-email" className="text-muted-foreground">
          {email}
        </span>
      ) : null}

      {!isAuthenticated ? (
        <Link href="/login" className="underline-offset-4 hover:underline">
          Login
        </Link>
      ) : (
        <button
          data-testid="nav-logout"
          onClick={onLogout}
          className="underline-offset-4 hover:underline"
        >
          Logout
        </button>
      )}
    </>
  );
}
