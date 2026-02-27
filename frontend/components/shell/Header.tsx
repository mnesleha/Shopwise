import Link from "next/link";
import { ShoppingCart } from "lucide-react";
import HeaderAuthClient from "@/components/shell/HeaderAuthClient";
import HeaderLeftSlotClient from "@/components/shell/HeaderLeftSlotClient";
import { CartBadgeClient } from "@/components/shell/CartBadgeClient";

export default function Header() {
  return (
    <header className="border-b">
      <div className="mx-auto w-full max-w-6xl px-4 py-4 flex items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <HeaderLeftSlotClient />
          <Link href="/products" className="font-semibold tracking-tight">
            Shopwise
          </Link>
        </div>

        <nav className="flex items-center gap-4 text-sm">
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
