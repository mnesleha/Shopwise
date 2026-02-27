"use client";

import * as React from "react";
import { X, LayoutGrid, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

interface Category {
  id: number;
  name: string;
}

interface CategorySidebarProps {
  isOpen: boolean;
  categories: Category[];
  selectedCategoryId?: number | null;
  onSelectCategory: (id: number | null) => void;
  onClose: () => void;
  onOpen: () => void;
}

export function CategorySidebar({
  isOpen,
  categories,
  selectedCategoryId,
  onSelectCategory,
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
          <h2 className="text-base font-semibold tracking-tight">Categories</h2>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label="Close category sidebar"
          >
            <X className="size-4" />
          </Button>
        </div>

        <Separator />

        {/* Category list */}
        <nav className="flex-1 overflow-y-auto px-3 py-3">
          <ul role="list" className="flex flex-col gap-1">
            {/* "All products" item */}
            <li>
              <button
                type="button"
                onClick={() => onSelectCategory(null)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  selectedCategoryId == null
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                )}
                aria-current={selectedCategoryId == null ? "page" : undefined}
              >
                <LayoutGrid className="size-4 shrink-0" />
                All products
              </button>
            </li>

            {/* Category items */}
            {categories.map((cat) => {
              const isSelected = selectedCategoryId === cat.id;
              return (
                <li key={cat.id}>
                  <button
                    type="button"
                    onClick={() => onSelectCategory(cat.id)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      isSelected
                        ? "bg-sidebar-primary text-sidebar-primary-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    )}
                    aria-current={isSelected ? "page" : undefined}
                  >
                    <span className="truncate">{cat.name}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer hint */}
        <Separator />
        <p className="px-5 py-3 text-xs text-muted-foreground">
          {categories.length}{" "}
          {categories.length === 1 ? "category" : "categories"}
        </p>
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
