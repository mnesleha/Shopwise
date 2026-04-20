import { Suspense } from "react";
import Link from "next/link";
import { ShoppingCart } from "lucide-react";
import HeaderAuthClient from "@/components/shell/HeaderAuthClient";
import HeaderLeftSlotClient from "@/components/shell/HeaderLeftSlotClient";
import HeaderSearchInput from "@/components/shell/HeaderSearchInput";
import { CartBadgeClient } from "@/components/shell/CartBadgeClient";

export default function Header() {
  return (
    // relative + z-50 keeps the header above the CategorySidebar backdrop (z-40)
    // so nav actions (logout, cart, etc.) remain tappable when the sidebar is open.
    <header className="relative z-50 border-b print:hidden">
      <div className="mx-auto w-full max-w-6xl px-4 py-4 flex items-center gap-4">
        <div className="flex items-baseline gap-3 shrink-0">
          <Suspense fallback={null}>
            <HeaderLeftSlotClient />
          </Suspense>
          <Link href="/products" className="font-semibold tracking-tight">
            Shopwise
          </Link>
          <Link href="/" className="text-sm">
            About
          </Link>
        </div>

        {/* Global product search — centered, grows to fill available space */}
        <div className="flex-1 flex justify-center">
          <Suspense fallback={<div className="w-full max-w-xs sm:max-w-sm" />}>
            <HeaderSearchInput />
          </Suspense>
        </div>

        <nav className="flex items-center gap-4 text-sm shrink-0 translate-y-1">
          <HeaderAuthClient />

          <Link
            data-testid="nav-cart"
            href="/cart"
            className="group relative inline-flex items-center gap-2 underline-offset-4 hover:underline"
            aria-label="Cart"
          >
            <ShoppingCart className="h-5 w-5" />
            <CartBadgeClient />
            <span className="pointer-events-none absolute top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-black px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
              Cart
            </span>
          </Link>
        </nav>
      </div>
    </header>
  );
}
