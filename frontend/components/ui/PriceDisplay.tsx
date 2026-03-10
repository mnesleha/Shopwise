/**
 * Shared pricing display primitives.
 *
 * Components
 * ----------
 * - `formatCurrency(currency, amount)` — "EUR 12.50", "$ 12.50"
 * - `DiscountBadge`   — badge shown inside the discount box
 * - `PriceDisplay`    — price block; when a discount is active renders a
 *                       vertical sticker: badge → discounted price → original
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
 * Badge rendered inside the PriceDisplay sticker box.
 * Uses an amber/yellow palette to contrast against the red background.
 */
export function DiscountBadge({ label, className }: DiscountBadgeProps) {
  return (
    <Badge
      data-testid="discount-badge"
      className={
        "bg-amber-400 text-red-900 hover:bg-amber-400 font-bold text-xs px-2 py-0.5 " +
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
   * from `price`, shown struck-through below the discounted price.
   */
  originalPrice?: string;
  /**
   * Short discount label shown in the badge at the top, e.g. "–10%".
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
 * Renders the price block.
 *
 * **No discount** — just the price, no extra chrome.
 *
 * **With discount** — vertical sticker box:
 * ```
 * ┌──────────────────────────┐
 * │  [BADGE: –10%]           │
 * │  EUR 44.99  (large)      │
 * │  ~~EUR 49.99~~  (small)  │
 * └──────────────────────────┘
 * ```
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

  // ── No-discount: plain inline price ──────────────────────────────────────
  if (!hasDiscount) {
    return (
      <div
        data-testid="price-display"
        className={"inline-flex items-center " + (className ?? "")}
      >
        <span
          data-testid="discounted-price"
          className={`${styles.price} text-foreground`}
        >
          {formatCurrency(currency, price)}
        </span>
      </div>
    );
  }

  // ── Discount sticker: badge → discounted price → original struck-through ─
  return (
    <div
      data-testid="price-display"
      className={
        "inline-flex flex-col items-start gap-1 rounded-md bg-red-500 px-3 py-2 " +
        (className ?? "")
      }
    >
      <DiscountBadge label={discountLabel!} />
      <span
        data-testid="discounted-price"
        className={`${styles.price} text-white leading-tight`}
      >
        {formatCurrency(currency, price)}
      </span>
      <span
        data-testid="original-price"
        className={`${styles.original} text-red-200 line-through leading-tight`}
      >
        {formatCurrency(currency, originalPrice!)}
      </span>
    </div>
  );
}
