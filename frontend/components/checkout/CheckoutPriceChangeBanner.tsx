"use client";

import * as React from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PriceChangePayload } from "@/lib/api/checkout";
import { overallDirection } from "@/lib/utils/priceChange";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CheckoutPriceChangeBannerProps {
  payload: PriceChangePayload;
  /**
   * When provided, renders a "View Order" action button.
   * Used in the post-checkout context.  Omit for the preflight (step 1) context
   * where the form's own Continue button handles progression.
   */
  onContinue?: () => void;
  /** Navigate back to the cart page. */
  onBackToCart: () => void;
  /**
   * Currency code used for price formatting.
   * Defaults to "EUR" — matches the demo backend's default currency.
   */
  currency?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Persistent WARNING-level banner shown on the checkout page after an order
 * is created with notable price changes.
 *
 * Does not block the customer — they can continue to their order ("View
 * Order") or navigate back to the cart ("Back to Cart").
 *
 * For INFO-level changes, use a toast instead (see checkout page).
 */
export function CheckoutPriceChangeBanner({
  payload,
  onContinue,
  onBackToCart,
  currency = "EUR",
}: CheckoutPriceChangeBannerProps) {
  const direction = overallDirection(payload.items);
  const isPositive = direction === "DOWN";

  const title = isPositive
    ? "Good news \u2014 your checkout total has decreased."
    : "Some prices in your cart have changed.";

  const Icon = isPositive ? TrendingDown : TrendingUp;

  // totalSavings is only computed when overallDirection === "DOWN" (isPositive guard),
  // so absolute_change values are safely treated as positive magnitudes — they represent
  // amounts saved, not signed differences.
  const totalSavings =
    isPositive && payload.items.length > 0
      ? payload.items
          .reduce((sum, item) => sum + parseFloat(item.absolute_change), 0)
          .toFixed(2)
      : null;

  return (
    <div data-testid="checkout-price-change-banner">
      <Alert
        className={cn(
          "border-2",
          isPositive
            ? "border-green-500 bg-green-50 dark:bg-green-950/20"
            : "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20",
        )}
      >
        <Icon
          className={cn(
            "h-4 w-4",
            isPositive ? "text-green-600" : "text-yellow-600",
          )}
        />
        <AlertTitle
          className={cn(
            isPositive
              ? "text-green-900 dark:text-green-100"
              : "text-yellow-900 dark:text-yellow-100",
          )}
        >
          {title}
        </AlertTitle>

        <AlertDescription>
          <div className="mt-2 flex flex-col gap-3">
            {/* Per-item price breakdown */}
            {payload.items.length > 0 && (
              <ul className="flex flex-col gap-1 text-sm">
                {payload.items.map((item) => (
                  <li
                    key={item.product_id}
                    data-testid={`price-change-item-${item.product_id}`}
                    className="flex flex-wrap items-baseline gap-1"
                  >
                    <span className="font-medium">{item.product_name}:</span>
                    <span className="text-muted-foreground">
                      {currency}&nbsp;{item.old_unit_gross}
                      {" \u2192 "}
                      {currency}&nbsp;{item.new_unit_gross}
                    </span>
                    <span
                      className={cn(
                        "text-xs font-medium",
                        item.direction === "DOWN"
                          ? "text-green-600"
                          : "text-yellow-700",
                      )}
                    >
                      ({item.direction === "DOWN" ? "\u2212" : "+"}
                      {item.percent_change}%)
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {/* Savings callout — only for all-DOWN carts */}
            {totalSavings !== null && (
              <p className="text-sm font-medium text-green-700 dark:text-green-300">
                Your total decreased by {currency}&nbsp;{totalSavings}.
              </p>
            )}

            {/* Action row */}
            <div className="flex gap-2 mt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={onBackToCart}
                data-testid="checkout-price-change-back"
              >
                Back to Cart
              </Button>
              {onContinue && (
                <Button
                  size="sm"
                  onClick={onContinue}
                  data-testid="checkout-price-change-continue"
                >
                  View Order
                </Button>
              )}
            </div>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
}
