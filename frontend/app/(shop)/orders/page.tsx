import { apiFetch } from "@/lib/server-fetch";
import {
  OrderHistoryTable,
  type OrderRowVm,
} from "@/components/orders/OrderHistoryTable";
import { ChevronDown } from "lucide-react";
import { redirect } from "next/navigation";
import ResendVerificationButton from "@/components/auth/ResendVerificationButton";

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

type MeDto = {
  is_authenticated: boolean;
  email?: string;
  email_verified?: boolean;
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
  // SSR auth probe first (do not fetch orders if user is not allowed to see them)
  const me = await apiFetch<MeDto>("/api/v1/auth/me/", {
    forwardCookies: true,
  });

  if (!me?.is_authenticated) {
    redirect("/login");
  }

  if (!me?.email_verified) {
    const email = me?.email ?? "";
    return (
      <div className="mx-auto w-full max-w-2xl space-y-4">
        <div>
          <h1 className="text-2xl font-semibold">Order History</h1>
          <p className="text-muted-foreground">
            Please verify your email to access order history and claim guest
            orders.
          </p>
        </div>

        <div className="rounded-lg border p-6 space-y-3">
          <div className="space-y-1">
            <p className="font-medium">Email verification required</p>
            <p className="text-sm text-muted-foreground">
              We’ll send a verification link to your email address.
            </p>
            {email ? (
              <p className="text-sm">
                <span className="text-muted-foreground">Email:</span>{" "}
                <span className="font-medium">{email}</span>
              </p>
            ) : null}
          </div>

          {email ? (
            <ResendVerificationButton email={email} />
          ) : (
            <p className="text-sm text-muted-foreground">
              Could not determine your email address. Please re-login.
            </p>
          )}
        </div>
      </div>
    );
  }

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
    </div>
  );
}
