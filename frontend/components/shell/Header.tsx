import Link from "next/link";
import CategoriesNav from "./CategoriesNav";

export default function Header() {
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
          <Link href="/login" className="underline-offset-4 hover:underline">
            Login
          </Link>
          <Link href="/cart" className="underline-offset-4 hover:underline">
            Cart
          </Link>
        </nav>
      </div>
    </header>
  );
}
