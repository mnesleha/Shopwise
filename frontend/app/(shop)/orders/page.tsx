import { apiFetch } from "@/lib/server-fetch";
import {
  OrderHistoryTable,
  type OrderRowVm,
} from "@/components/orders/OrderHistoryTable";
import { ChevronDown } from "lucide-react";

type OrderItemDto = {
  id: number;
  product: number;
  quantity: number;
  unit_price: string;
  line_total: string;
  discount: null | { type: "FIXED" | "PERCENT"; value: string };
};

type OrderDto = {
  id: number;
  status: string;
  items: OrderItemDto[];
  total: string;
};

const COMPLETED_STATUSES = new Set(["DELIVERED", "CANCELLED"]);

function toRowVm(o: OrderDto): OrderRowVm {
  return {
    id: o.id,
    status: o.status,
    total: o.total,
    itemCount: (o.items ?? []).reduce((sum, it) => sum + (it.quantity ?? 0), 0),
  };
}

export default async function OrdersPage() {
  const orders = await apiFetch<OrderDto[]>("/api/v1/orders/", {
    forwardCookies: true,
  });

  const rows = (orders ?? []).map(toRowVm);

  const active = rows.filter((o) => !COMPLETED_STATUSES.has(o.status));
  const completed = rows.filter((o) => COMPLETED_STATUSES.has(o.status));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Order History</h1>
        <p className="text-muted-foreground">
          Your active and completed orders.
        </p>
      </div>

      <details className="group border-b" open>
        <summary className="flex cursor-pointer list-none items-center justify-between py-4">
          <span className="font-semibold text-lg text-foreground">
            Active orders ({active.length})
          </span>
          <ChevronDown className="h-5 w-5 transition-transform duration-300 group-open:rotate-180" />
        </summary>
        <div className="mt-3">
          <OrderHistoryTable title="Active orders" orders={active} />
        </div>
      </details>

      <details className="group border-b">
        <summary className="flex cursor-pointer list-none items-center justify-between py-4">
          <span className="font-semibold text-lg text-foreground">
            Completed orders ({completed.length})
          </span>
          <ChevronDown className="h-5 w-5 transition-transform duration-300 group-open:rotate-180" />
        </summary>
        <div className="mt-3">
          <OrderHistoryTable title="Completed orders" orders={completed} />
        </div>
      </details>

      {/* <div className="space-y-6">
        <OrderHistoryTable title="Active orders" orders={active} />
        <OrderHistoryTable title="Completed orders" orders={completed} />
      </div> */}
    </div>
  );
}
