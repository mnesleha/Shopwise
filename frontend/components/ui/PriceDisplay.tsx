/**
 * Shared pricing display primitives.
 *
 * Components
 * ----------
 * - `formatCurrency(currency, amount)` — "EUR 12.50", "$ 12.50"
 * - `DiscountBadge`   — coloured "–10 %" / "–EUR 5.00" badge
 * - `PriceDisplay`    — full block: [original struck-through] + discounted price + badge
 */

import * as React from "react";
import { Badge } from "@/components/ui/badge";

// ---------------------------------------------------------------------------
// Formatting helper
// ---------------------------------------------------------------------------

/**
 * Format a currency amount with a space between the symbol/code and amount.
 *
 * USD → "$\u00a0{amount}"  (non-breaking space)
 * EUR → "EUR\u00a0{amount}"
 */
export function formatCurrency(currency: string, amount: string): string {
  const symbol = currency === "USD" ? "$" : currency;
  return `${symbol}\u00a0${amount}`;
}

// ---------------------------------------------------------------------------
// DiscountBadge
// ---------------------------------------------------------------------------

interface DiscountBadgeProps {
  /** Human-readable label, e.g. "–10%" or "–EUR 5.00". */
  label: string;
  className?: string;
}

/**
 * A compact green badge showing the discount magnitude.
 */
export function DiscountBadge({ label, className }: DiscountBadgeProps) {
  return (
    <Badge
      data-testid="discount-badge"
      className={
        "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 font-semibold " +
        (className ?? "")
      }
    >
      {label}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// PriceDisplay
// ---------------------------------------------------------------------------

export interface PriceDisplayProps {
  /** Currency code, e.g. "EUR". */
  currency: string;
  /**
   * The visible (discounted) gross price.  Always shown prominently.
   */
  price: string;
  /**
   * The original gross price before discount.  When provided and different
   * from `price`, shown struck-through above the discounted price.
   */
  originalPrice?: string;
  /**
   * Short discount label shown as a badge, e.g. "–10%" or "–EUR 5.00".
   * When provided a `DiscountBadge` is rendered next to the prices.
   */
  discountLabel?: string;
  /**
   * Size variant — affects text sizing only.
   * - "sm"  → used in cart item rows (font-semibold text-sm)
   * - "md"  → used in product cards (text-xl font-bold)   [default]
   * - "lg"  → used in product detail (text-3xl font-bold)
   */
  size?: "sm" | "md" | "lg";
  className?: string;
}

const _sizeMap: Record<
  "sm" | "md" | "lg",
  { price: string; original: string }
> = {
  sm: { price: "text-sm font-semibold", original: "text-xs" },
  md: { price: "text-xl font-bold", original: "text-sm" },
  lg: { price: "text-3xl font-bold", original: "text-base" },
};

/**
 * Renders the discount-aware price block.
 *
 * When no `originalPrice` / `discountLabel` are provided it renders just the
 * price (same as before — backwards compatible).
 */
export function PriceDisplay({
  currency,
  price,
  originalPrice,
  discountLabel,
  size = "md",
  className,
}: PriceDisplayProps) {
  const hasDiscount = Boolean(
    originalPrice && originalPrice !== price && discountLabel,
  );
  const styles = _sizeMap[size];

  return (
    <div
      data-testid="price-display"
      className={"flex flex-wrap items-center gap-1.5 " + (className ?? "")}
    >
      {hasDiscount && (
        <span
          data-testid="original-price"
          className={`${styles.original} text-muted-foreground line-through`}
        >
          {formatCurrency(currency, originalPrice!)}
        </span>
      )}
      <span
        data-testid="discounted-price"
        className={`${styles.price} ${hasDiscount ? "text-emerald-600 dark:text-emerald-400" : "text-foreground"}`}
      >
        {formatCurrency(currency, price)}
      </span>
      {hasDiscount && discountLabel && <DiscountBadge label={discountLabel} />}
    </div>
  );
}
