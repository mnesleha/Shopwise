"use client";

import * as React from "react";
import { flushSync } from "react-dom";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api/auth";
import { ClipboardList, UserCircle } from "lucide-react";
import { useAuth } from "@/components/auth/AuthProvider";

export default function HeaderAuthClient() {
  const router = useRouter();
  const { isAuthenticated, email, firstName, lastName, setAnonymous } =
    useAuth();

  const onLogout = async () => {
    await logout();
    // flushSync forces React to synchronously commit the state update to the DOM
    // before router.push starts its navigation transition. Without this, React 18
    // batches the setState calls and defers them into the concurrent transition,
    // which means on slow mobile connections the header visibly stays authenticated
    // for the entire duration of the navigation (until the new page settles).
    flushSync(() => setAnonymous());
    // Do NOT call refreshCart() here: it fires an authenticated request which
    // gets 401 after logout, triggers the interceptor retry → window.location.assign
    // which conflicts with router.push on slow mobile connections.
    // The ShopLayout SSR re-fetches the cart on the next navigation and
    // reinitialises CartProvider with count=0 automatically.
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
