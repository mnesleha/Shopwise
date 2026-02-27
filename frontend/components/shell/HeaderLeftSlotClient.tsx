"use client";

import { usePathname, useSearchParams } from "next/navigation";
import CategoryFilterSlot from "@/components/product/CategoryFilterSlot";

export default function HeaderLeftSlotClient() {
  const pathname = usePathname();
  const sp = useSearchParams();

  if (!pathname?.startsWith("/products")) return null;

  const categoryParam = sp.get("category");
  const selectedCategoryId = categoryParam ? Number(categoryParam) : null;

  return <CategoryFilterSlot selectedCategoryId={selectedCategoryId} />;
}
