import { describe, expect, it } from "vitest";

import { splitOrdersByCompletion } from "@/app/(shop)/orders/grouping";

describe("splitOrdersByCompletion", () => {
  it("keeps delivery failure orders outside completed outcomes", () => {
    const rows = [
      { id: 1, status: "PAID", total: "100.00", itemCount: 1 },
      { id: 2, status: "DELIVERED", total: "50.00", itemCount: 2 },
      { id: 3, status: "DELIVERY_FAILED", total: "20.00", itemCount: 1 },
      { id: 4, status: "FAILED_DELIVERY", total: "30.00", itemCount: 1 },
      { id: 5, status: "CANCELLED", total: "80.00", itemCount: 3 },
    ];

    const { active, completed } = splitOrdersByCompletion(rows);

    expect(active.map((order) => order.id)).toEqual([1, 3, 4]);
    expect(completed.map((order) => order.id)).toEqual([2, 5]);
  });
});
