"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { logout } from "@/lib/api/auth";
import CategoriesNav from "./CategoriesNav";
import { use } from "react";

export default function Header() {
  const { isAuthenticated, email, refresh, setAnonymous } = useAuth();
  const router = useRouter();

  const onLogout = async () => {
    await logout();
    setAnonymous();
    router.push("/products");
  };

  return (
    <header className="border-b">
      <div className="mx-auto w-full max-w-6xl px-4 py-4 flex items-center justify-between gap-6">
        <div className="flex items-center gap-6">
          <Link href="/products" className="font-semibold tracking-tight">
            Shopwise
          </Link>
          <CategoriesNav />
        </div>

        <nav className="flex items-center gap-4 text-sm">
          {isAuthenticated ? (
            <>
              <span>{email}</span>
              <button
                onClick={onLogout}
                className="underline-offset-4 hover:underline"
              >
                Logout
              </button>
            </>
          ) : (
            <Link href="/login" className="underline-offset-4 hover:underline">
              Login
            </Link>
          )}
          <Link href="/cart" className="underline-offset-4 hover:underline">
            Cart
          </Link>
        </nav>
      </div>
    </header>
  );
}
