"use client";

import * as React from "react";
import { X, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import CatalogFilterPanel from "@/components/product/CatalogFilterPanel";

interface Category {
  id: number;
  name: string;
}

interface CategorySidebarProps {
  isOpen: boolean;
  categories: Category[];
  priceBoundsMin: string | null;
  priceBoundsMax: string | null;
  searchParamsString: string;
  onClose: () => void;
  onOpen: () => void;
}

export function CategorySidebar({
  isOpen,
  categories,
  priceBoundsMin,
  priceBoundsMax,
  searchParamsString,
  onClose,
  onOpen,
}: CategorySidebarProps) {
  return (
    <>
      {/* Backdrop overlay — visible only when open */}
      <div
        className={cn(
          "fixed inset-0 z-40 bg-foreground/20 transition-opacity duration-300 md:hidden",
          isOpen
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0",
        )}
        aria-hidden="true"
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-lg transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Category navigation"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4">
          <h2 className="text-base font-semibold tracking-tight">Filters</h2>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label="Close filters"
          >
            <X className="size-4" />
          </Button>
        </div>

        <Separator />

        {/* Filter panel */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <CatalogFilterPanel
            categories={categories}
            priceBoundsMin={priceBoundsMin}
            priceBoundsMax={priceBoundsMax}
            searchParamsString={searchParamsString}
          />
        </div>
      </aside>

      {/* Edge handle — visible when closed */}
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          "fixed left-0 top-1/2 z-40 -translate-y-1/2 rounded-r-lg border border-l-0 border-sidebar-border bg-sidebar px-1 py-6 text-sidebar-foreground shadow-md transition-opacity duration-300 hover:bg-sidebar-accent",
          isOpen ? "pointer-events-none opacity-0" : "opacity-100",
        )}
        aria-label="Open category sidebar"
      >
        <ChevronRight className="size-4" />
      </button>
    </>
  );
}
