/**
 * Unit tests for getPriceChangeMessage() and overallDirection() helpers.
 *
 * These are pure functions — no rendering, no mocks.
 *
 * Spec coverage:
 * - no message for NONE severity
 * - no message when has_changes is false
 * - INFO + UP  → subtle upward message
 * - INFO + DOWN → positive downward message
 * - WARNING + UP → warning upward message
 * - WARNING + DOWN → positive downward message ("Good news")
 * - INFO + MIXED → neutral message
 * - WARNING + MIXED → neutral warning message
 */
import { describe, it, expect } from "vitest";
import {
  overallDirection,
  getPriceChangeMessage,
} from "@/lib/utils/priceChange";
import type { PriceChangeItem, PriceChangePayload } from "@/lib/api/checkout";

// ---------------------------------------------------------------------------
// Fixture factories
// ---------------------------------------------------------------------------

function makeItem(
  direction: "UP" | "DOWN",
  overrides: Partial<PriceChangeItem> = {},
): PriceChangeItem {
  return {
    product_id: 1,
    product_name: "Widget",
    old_unit_gross: "10.00",
    new_unit_gross: direction === "UP" ? "11.00" : "9.00",
    absolute_change: "1.00",
    percent_change: "10.00",
    direction,
    severity: "INFO",
    ...overrides,
  };
}

function makePayload(
  overrides: Partial<PriceChangePayload> = {},
): PriceChangePayload {
  return {
    has_changes: true,
    severity: "INFO",
    affected_items: 1,
    items: [makeItem("UP")],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// overallDirection
// ---------------------------------------------------------------------------

describe("overallDirection", () => {
  it("returns UP when every item went up", () => {
    expect(overallDirection([makeItem("UP"), makeItem("UP")])).toBe("UP");
  });

  it("returns DOWN when every item went down", () => {
    expect(overallDirection([makeItem("DOWN"), makeItem("DOWN")])).toBe("DOWN");
  });

  it("returns MIXED when items have different directions", () => {
    expect(overallDirection([makeItem("UP"), makeItem("DOWN")])).toBe("MIXED");
  });

  it("returns MIXED for an empty items array", () => {
    expect(overallDirection([])).toBe("MIXED");
  });
});

// ---------------------------------------------------------------------------
// getPriceChangeMessage
// ---------------------------------------------------------------------------

describe("getPriceChangeMessage", () => {
  describe("returns null when there is nothing to communicate", () => {
    it("returns null for severity NONE", () => {
      const payload = makePayload({ severity: "NONE", has_changes: false });
      expect(getPriceChangeMessage(payload)).toBeNull();
    });

    it("returns null when has_changes is false even if severity is INFO", () => {
      const payload = makePayload({ has_changes: false, severity: "INFO" });
      expect(getPriceChangeMessage(payload)).toBeNull();
    });
  });

  describe("INFO severity — subtle messaging", () => {
    it("INFO + UP → subtle upward message", () => {
      const payload = makePayload({
        severity: "INFO",
        items: [makeItem("UP")],
      });
      expect(getPriceChangeMessage(payload)).toBe(
        "The price of one or more items changed slightly.",
      );
    });

    it("INFO + DOWN → positive downward message", () => {
      const payload = makePayload({
        severity: "INFO",
        items: [makeItem("DOWN")],
      });
      expect(getPriceChangeMessage(payload)).toMatch(/good news/i);
      expect(getPriceChangeMessage(payload)).toMatch(/decreased/i);
    });

    it("INFO + MIXED → neutral message", () => {
      const payload = makePayload({
        severity: "INFO",
        items: [makeItem("UP"), makeItem("DOWN")],
      });
      expect(getPriceChangeMessage(payload)).toBe(
        "The price of one or more items has changed.",
      );
    });
  });

  describe("WARNING severity — explicit messaging", () => {
    it("WARNING + UP → warning upward message", () => {
      const payload = makePayload({
        severity: "WARNING",
        items: [makeItem("UP", { severity: "WARNING" })],
      });
      expect(getPriceChangeMessage(payload)).toBe(
        "Some prices in your cart have changed.",
      );
    });

    it("WARNING + DOWN → positive downward message mentioning total", () => {
      const payload = makePayload({
        severity: "WARNING",
        items: [makeItem("DOWN", { severity: "WARNING" })],
      });
      const msg = getPriceChangeMessage(payload);
      expect(msg).toMatch(/good news/i);
      expect(msg).toMatch(/total/i);
      expect(msg).toMatch(/decreased/i);
    });

    it("WARNING + MIXED → neutral warning message", () => {
      const payload = makePayload({
        severity: "WARNING",
        items: [makeItem("UP"), makeItem("DOWN")],
      });
      expect(getPriceChangeMessage(payload)).toBe(
        "Some prices in your cart have changed.",
      );
    });
  });
});
