"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Use a sentinel string for "no sort / default" because shadcn SelectItem
// does not accept an empty string value.
const SORT_NONE = "__none__";

const SORT_OPTIONS = [
  { value: SORT_NONE, label: "Default" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
  { value: "name_asc", label: "Name: A to Z" },
  { value: "name_desc", label: "Name: Z to A" },
] as const;

export default function SortDropdown() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentSort = searchParams?.get("sort") ?? SORT_NONE;

  const handleChange = (value: string) => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.delete("page"); // reset pagination on sort change

    if (value && value !== SORT_NONE) {
      params.set("sort", value);
    } else {
      params.delete("sort");
    }

    const qs = params.toString();
    router.replace(qs ? `/products?${qs}` : "/products");
  };

  return (
    <div className="flex items-center gap-2 shrink-0">
      <span className="text-sm text-muted-foreground whitespace-nowrap">
        Sort by
      </span>
      <Select value={currentSort} onValueChange={handleChange}>
        <SelectTrigger className="w-44" data-testid="sort-select">
          <SelectValue placeholder="Default" />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
