"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { CategorySidebar } from "@/components/product/CategorySidebar";
import { FilterToggleButton } from "@/components/product/FilterToggleButton";

type Category = { id: number; name: string };
type ProductsMeta = {
  metadata: {
    price_min_available: string | null;
    price_max_available: string | null;
  };
};

export default function CategoryFilterSlot() {
  const searchParams = useSearchParams();
  const [isOpen, setIsOpen] = React.useState(false);
  const [categories, setCategories] = React.useState<Category[]>([]);
  const [priceBoundsMin, setPriceBoundsMin] = React.useState<string | null>(
    null,
  );
  const [priceBoundsMax, setPriceBoundsMax] = React.useState<string | null>(
    null,
  );

  React.useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const [catsRes, metaRes] = await Promise.all([
          api.get<Category[]>("/categories/"),
          api.get<ProductsMeta>("/products/"),
        ]);
        if (!mounted) return;
        setCategories(catsRes.data);
        setPriceBoundsMin(metaRes.data.metadata.price_min_available ?? null);
        setPriceBoundsMax(metaRes.data.metadata.price_max_available ?? null);
      } catch {
        // non-critical — sidebar still works without data
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <>
      <FilterToggleButton
        isOpen={isOpen}
        onToggle={() => setIsOpen((p) => !p)}
      />

      <CategorySidebar
        isOpen={isOpen}
        categories={categories}
        priceBoundsMin={priceBoundsMin}
        priceBoundsMax={priceBoundsMax}
        searchParamsString={searchParams?.toString() ?? ""}
        onClose={() => setIsOpen(false)}
        onOpen={() => setIsOpen(true)}
      />
    </>
  );
}
