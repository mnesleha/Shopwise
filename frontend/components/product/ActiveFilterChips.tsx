"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Category {
  id: number;
  name: string;
}

interface ActiveFilterChipsProps {
  categories: Category[];
}

/** Returns a copy of URLSearchParams with the supplied key removed (first occurrence). */
function removeParam(
  params: URLSearchParams,
  key: string,
  value?: string,
): URLSearchParams {
  const next = new URLSearchParams(params.toString());
  if (value !== undefined) {
    // Remove a single occurrence of key=value from a multi-value key
    const existing = next.getAll(key).filter((v) => v !== value);
    next.delete(key);
    existing.forEach((v) => next.append(key, v));
  } else {
    next.delete(key);
  }
  next.delete("page"); // reset pagination whenever a filter is cleared
  return next;
}

export default function ActiveFilterChips({
  categories,
}: ActiveFilterChipsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const selectedCategoryIds = searchParams?.getAll("category") ?? [];
  const minPrice = searchParams?.get("min_price") ?? "";
  const maxPrice = searchParams?.get("max_price") ?? "";
  const inStockOnly = searchParams?.get("in_stock_only") === "true";

  const hasActiveFilters =
    selectedCategoryIds.length > 0 || minPrice || maxPrice || inStockOnly;

  if (!hasActiveFilters) return null;

  const navigate = (params: URLSearchParams) => {
    const qs = params.toString();
    router.replace(qs ? `/products?${qs}` : "/products");
  };

  const clearAll = () => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.delete("category");
    params.delete("min_price");
    params.delete("max_price");
    params.delete("in_stock_only");
    params.delete("page");
    navigate(params);
  };

  const categoryMap = new Map(categories.map((c) => [String(c.id), c.name]));

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      data-testid="active-filter-chips"
    >
      {selectedCategoryIds.map((id) => (
        <Badge
          key={`cat-${id}`}
          variant="secondary"
          className="flex items-center gap-1"
          data-testid={`chip-category-${id}`}
        >
          {categoryMap.get(id) ?? `Category ${id}`}
          <button
            aria-label={`Remove category filter`}
            onClick={() =>
              navigate(
                removeParam(
                  searchParams ?? new URLSearchParams(),
                  "category",
                  id,
                ),
              )
            }
            className="ml-0.5 rounded-full hover:bg-accent"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}

      {minPrice && (
        <Badge
          variant="secondary"
          className="flex items-center gap-1"
          data-testid="chip-min-price"
        >
          From ${minPrice}
          <button
            aria-label="Remove min price filter"
            onClick={() =>
              navigate(
                removeParam(searchParams ?? new URLSearchParams(), "min_price"),
              )
            }
            className="ml-0.5 rounded-full hover:bg-accent"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}

      {maxPrice && (
        <Badge
          variant="secondary"
          className="flex items-center gap-1"
          data-testid="chip-max-price"
        >
          To ${maxPrice}
          <button
            aria-label="Remove max price filter"
            onClick={() =>
              navigate(
                removeParam(searchParams ?? new URLSearchParams(), "max_price"),
              )
            }
            className="ml-0.5 rounded-full hover:bg-accent"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}

      {inStockOnly && (
        <Badge
          variant="secondary"
          className="flex items-center gap-1"
          data-testid="chip-in-stock"
        >
          In stock
          <button
            aria-label="Remove in-stock filter"
            onClick={() =>
              navigate(
                removeParam(
                  searchParams ?? new URLSearchParams(),
                  "in_stock_only",
                ),
              )
            }
            className="ml-0.5 rounded-full hover:bg-accent"
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      )}

      <Button
        variant="ghost"
        size="sm"
        onClick={clearAll}
        className="h-6 px-2 text-xs"
        data-testid="clear-all-filters"
      >
        Clear all
      </Button>
    </div>
  );
}
