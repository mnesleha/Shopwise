"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api/auth";
import { ClipboardList, UserCircle } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";
import { useCart } from "@/components/cart/CartProvider";

export default function HeaderAuthClient() {
  const router = useRouter();
  const { isAuthenticated, email, firstName, lastName, setAnonymous } = useAuth();
  const { refreshCart } = useCart();

  const onLogout = async () => {
    await logout();
    setAnonymous();
    await refreshCart(); // re-fetch anonymous (empty) cart — resets badge to 0
    router.push("/products");
  };

  return (
    <>
      {isAuthenticated ? (
        <Link
          href="/orders"
          data-testid="nav-orders"
          className="group relative inline-flex items-center gap-2 underline-offset-4 hover:underline"
          aria-label="Orders"
        >
          <ClipboardList className="h-5 w-5" />
          <span className="pointer-events-none absolute top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-black px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
            Orders
          </span>
        </Link>
      ) : null}
      {isAuthenticated && (email || firstName || lastName) ? (
        <span data-testid="auth-user-label" className="text-muted-foreground">
          {/* Prefer full name; fall back to email */}
          {`${firstName ?? ""} ${lastName ?? ""}`.trim() || email}
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
      <Link
        href={isAuthenticated ? "/profile" : "/login"}
        data-testid="nav-profile"
        className="group relative inline-flex items-center gap-2 underline-offset-4 hover:underline"
        aria-label="Profile"
      >
        <UserCircle className="h-5 w-5" />
        <span className="pointer-events-none absolute top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-black px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
          Profile
        </span>
      </Link>
    </>
  );
}
