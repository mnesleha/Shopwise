"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { CategorySidebar } from "@/components/product/CategorySidebar";
import { FilterToggleButton } from "@/components/product/FilterToggleButton";

type Category = { id: number; name: string };

type Props = {
  selectedCategoryId?: number | null;
};

export default function CategoryFilterSlot({ selectedCategoryId }: Props) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [categories, setCategories] = React.useState<Category[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);

  const router = useRouter();
  const searchParams = useSearchParams();

  React.useEffect(() => {
    let mounted = true;

    async function load() {
      setIsLoading(true);
      try {
        const res = await api.get<Category[]>("/categories/");
        if (mounted) setCategories(res.data);
      } finally {
        if (mounted) setIsLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  const onToggle = () => setIsOpen((p) => !p);

  const onSelectCategory = (id: number | null) => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");

    // reset paging when filter changes
    params.delete("page");

    if (id) params.set("category", String(id));
    else params.delete("category");

    const qs = params.toString();
    router.push(qs ? `/products?${qs}` : "/products");
    setIsOpen(false);
  };

  return (
    <>
      <FilterToggleButton isOpen={isOpen} onToggle={onToggle} />

      <CategorySidebar
        isOpen={isOpen}
        categories={isLoading ? [] : categories}
        selectedCategoryId={selectedCategoryId ?? null}
        onSelectCategory={onSelectCategory}
        onClose={() => setIsOpen(false)}
        onOpen={() => setIsOpen(true)}
      />
    </>
  );
}
