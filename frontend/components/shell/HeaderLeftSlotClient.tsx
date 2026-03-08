"use client";

import { usePathname } from "next/navigation";
import CategoryFilterSlot from "@/components/product/CategoryFilterSlot";

export default function HeaderLeftSlotClient() {
  const pathname = usePathname();

  if (!pathname?.startsWith("/products")) return null;

  return <CategoryFilterSlot />;
}
