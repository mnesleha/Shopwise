import type { OrderRowVm } from "@/components/orders/OrderHistoryTable";

export const COMPLETED_STATUSES = new Set([
  "DELIVERED",
  "CANCELLED",
]);

export function splitOrdersByCompletion(rows: OrderRowVm[]): {
  active: OrderRowVm[];
  completed: OrderRowVm[];
} {
  return {
    active: rows.filter((order) => !COMPLETED_STATUSES.has(order.status)),
    completed: rows.filter((order) => COMPLETED_STATUSES.has(order.status)),
  };
}