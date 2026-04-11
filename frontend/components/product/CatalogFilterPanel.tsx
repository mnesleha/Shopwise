"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

interface Category {
  id: number;
  name: string;
}

interface CatalogFilterPanelProps {
  categories: Category[];
  priceBoundsMin: string | null;
  priceBoundsMax: string | null;
}

const DEBOUNCE_MS = 300;

export default function CatalogFilterPanel({
  categories,
  priceBoundsMin,
  priceBoundsMax,
}: CatalogFilterPanelProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // ─── Category state ───────────────────────────────────────────────────────
  const selectedIds = new Set(searchParams?.getAll("category") ?? []);

  const toggleCategory = (id: number) => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.delete("page"); // reset pagination
    const key = String(id);
    const existing = params.getAll("category").filter((v) => v !== key);
    params.delete("category");
    if (selectedIds.has(key)) {
      // deselect — keep remaining
      existing.forEach((v) => params.append("category", v));
    } else {
      // select — add this one
      [...existing, key].forEach((v) => params.append("category", v));
    }
    const qs = params.toString();
    router.replace(qs ? `/products?${qs}` : "/products");
  };

  // ─── Price state (local, debounced) ───────────────────────────────────────
  const boundsMin =
    priceBoundsMin !== null ? Math.floor(parseFloat(priceBoundsMin)) : 0;
  const boundsMax =
    priceBoundsMax !== null ? Math.ceil(parseFloat(priceBoundsMax)) : 100000;

  const urlMin = searchParams?.get("min_price") ?? "";
  const urlMax = searchParams?.get("max_price") ?? "";

  const [localMin, setLocalMin] = React.useState<string>(urlMin);
  const [localMax, setLocalMax] = React.useState<string>(urlMax);

  // Keep local values in sync when URL changes (e.g. chip clear)
  React.useEffect(() => {
    setLocalMin(urlMin);
  }, [urlMin]);
  React.useEffect(() => {
    setLocalMax(urlMax);
  }, [urlMax]);

  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const commitPrice = (min: string, max: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      params.delete("page");
      if (min) params.set("min_price", min);
      else params.delete("min_price");
      if (max) params.set("max_price", max);
      else params.delete("max_price");
      const qs = params.toString();
      router.replace(qs ? `/products?${qs}` : "/products");
    }, DEBOUNCE_MS);
  };

  const handleSliderChange = ([lo, hi]: number[]) => {
    const minStr = lo > boundsMin ? String(lo) : "";
    const maxStr = hi < boundsMax ? String(hi) : "";
    setLocalMin(minStr);
    setLocalMax(maxStr);
    commitPrice(minStr, maxStr);
  };

  const handleMinInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/[^0-9.]/g, "");
    setLocalMin(val);
    commitPrice(val, localMax);
  };

  const handleMaxInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/[^0-9.]/g, "");
    setLocalMax(val);
    commitPrice(localMin, val);
  };

  // Derived slider values (fall back to bounds endpoints)
  const sliderLo = localMin
    ? Math.max(boundsMin, parseFloat(localMin) || boundsMin)
    : boundsMin;
  const sliderHi = localMax
    ? Math.min(boundsMax, parseFloat(localMax) || boundsMax)
    : boundsMax;

  // ─── In-stock ─────────────────────────────────────────────────────────────
  const inStockOnly = searchParams?.get("in_stock_only") === "true";

  const toggleInStock = () => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.delete("page");
    if (inStockOnly) {
      params.delete("in_stock_only");
    } else {
      params.set("in_stock_only", "true");
    }
    const qs = params.toString();
    router.replace(qs ? `/products?${qs}` : "/products");
  };

  return (
    <aside
      className="flex w-full flex-col gap-6"
      data-testid="catalog-filter-panel"
    >
      {/* ── Categories ─────────────────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold mb-3">Categories</h3>
        {categories.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No categories available.
          </p>
        ) : (
          <ul className="max-h-60 overflow-y-auto pr-2 space-y-2">
            {categories.map((cat) => (
              <li key={cat.id} className="flex items-center gap-2">
                <Checkbox
                  id={`cat-${cat.id}`}
                  data-testid={`category-checkbox-${cat.id}`}
                  checked={selectedIds.has(String(cat.id))}
                  onCheckedChange={() => toggleCategory(cat.id)}
                  className="border-foreground/20 bg-background shadow-none data-[state=checked]:border-primary focus-visible:ring-sidebar-ring/35"
                />
                <Label
                  htmlFor={`cat-${cat.id}`}
                  className="cursor-pointer text-sm font-normal"
                >
                  {cat.name}
                </Label>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Separator />

      {/* ── Price ──────────────────────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold mb-3">Price</h3>
        <Slider
          data-testid="price-slider"
          min={boundsMin}
          max={boundsMax}
          step={1}
          value={[sliderLo, sliderHi]}
          onValueChange={handleSliderChange}
          className="mb-4"
        />
        <div className="flex items-center gap-2">
          <Input
            data-testid="price-min-input"
            type="text"
            inputMode="decimal"
            placeholder={String(boundsMin)}
            value={localMin}
            onChange={handleMinInput}
            className="h-8 border-foreground/20 bg-background text-sm shadow-none"
            aria-label="Minimum price"
          />
          <span className="text-muted-foreground text-xs shrink-0">–</span>
          <Input
            data-testid="price-max-input"
            type="text"
            inputMode="decimal"
            placeholder={String(boundsMax)}
            value={localMax}
            onChange={handleMaxInput}
            className="h-8 border-foreground/20 bg-background text-sm shadow-none"
            aria-label="Maximum price"
          />
        </div>
      </section>

      <Separator />

      {/* ── Availability ───────────────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold mb-3">Availability</h3>
        <div className="flex items-center gap-2">
          <Checkbox
            id="in-stock-only"
            data-testid="in-stock-checkbox"
            checked={inStockOnly}
            onCheckedChange={toggleInStock}
            className="border-foreground/20 bg-background shadow-none data-[state=checked]:border-primary focus-visible:ring-sidebar-ring/35"
          />
          <Label
            htmlFor="in-stock-only"
            className="cursor-pointer text-sm font-normal"
          >
            In stock only
          </Label>
        </div>
      </section>
    </aside>
  );
}
