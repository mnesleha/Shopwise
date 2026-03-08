"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search } from "lucide-react";

/** Query params that are scoped to a specific filter context and should be
 *  cleared whenever the user starts a new global search. */
const FILTER_PARAMS = [
  "category",
  "min_price",
  "max_price",
  "in_stock_only",
  "sort",
  "page",
];

export default function HeaderSearchInput() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Mirror the current URL search param into local state so the input
  // reflects the active query when navigating back to /products.
  const [value, setValue] = React.useState(searchParams?.get("search") ?? "");

  // Keep local state in sync when the URL changes (e.g. chip "clear all").
  React.useEffect(() => {
    setValue(searchParams?.get("search") ?? "");
  }, [searchParams]);

  const submit = () => {
    const params = new URLSearchParams();
    // Strip all filter/sort params; keep only the new search term.
    FILTER_PARAMS.forEach((k) => params.delete(k));
    const trimmed = value.trim();
    if (trimmed) params.set("search", trimmed);
    const qs = params.toString();
    router.push(qs ? `/products?${qs}` : "/products");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") submit();
  };

  return (
    <div className="relative flex w-full max-w-xs sm:max-w-sm items-center">
      {/* Clickable search icon — submits on click */}
      <button
        type="button"
        onClick={submit}
        aria-label="Search"
        className="absolute left-3 text-muted-foreground hover:text-foreground transition-colors"
        tabIndex={-1}
      >
        <Search className="h-4 w-4" />
      </button>

      <input
        type="search"
        data-testid="header-search-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Search products and descriptions..."
        className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
        aria-label="Search products"
      />
    </div>
  );
}
