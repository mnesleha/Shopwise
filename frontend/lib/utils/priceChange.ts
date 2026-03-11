import type { PriceChangeItem, PriceChangePayload } from "@/lib/api/checkout";

// ---------------------------------------------------------------------------
// Direction helpers
// ---------------------------------------------------------------------------

/**
 * Determine the overall price-change direction across all affected items.
 *
 * Returns:
 * - "UP"    — every changed item went up
 * - "DOWN"  — every changed item went down
 * - "MIXED" — items changed in different directions (or no items)
 */
export function overallDirection(
  items: PriceChangeItem[],
): "UP" | "DOWN" | "MIXED" {
  if (items.length === 0) return "MIXED";
  const dirs = new Set(items.map((i) => i.direction));
  if (dirs.size === 1) {
    return dirs.values().next().value as "UP" | "DOWN";
  }
  return "MIXED";
}

// ---------------------------------------------------------------------------
// Message generation
// ---------------------------------------------------------------------------

/**
 * Return a short, direction-aware notification message for checkout
 * price-change events.
 *
 * - Returns null for NONE severity or when there are no changes.
 * - Tone is proportional to severity: subtle for INFO, explicit for WARNING.
 * - Messaging is direction-aware: positive framing for price decreases,
 *   neutral framing for mixed changes.
 */
export function getPriceChangeMessage(
  payload: PriceChangePayload,
): string | null {
  if (!payload.has_changes || payload.severity === "NONE") return null;

  const direction = overallDirection(payload.items);
  const { severity } = payload;

  if (direction === "DOWN") {
    if (severity === "INFO")
      return "Good news \u2014 the price of one or more items has decreased.";
    if (severity === "WARNING")
      return "Good news \u2014 your checkout total has decreased.";
  }

  if (direction === "UP") {
    if (severity === "INFO")
      return "The price of one or more items changed slightly.";
    if (severity === "WARNING") return "Some prices in your cart have changed.";
  }

  // MIXED direction
  if (severity === "INFO") return "The price of one or more items has changed.";
  return "Some prices in your cart have changed.";
}
