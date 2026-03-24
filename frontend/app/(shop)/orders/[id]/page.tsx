import { getOrderServer } from "@/lib/server/orders";
import { mapOrderToVm } from "@/lib/mappers/orders";
import OrderDetailClient from "@/components/order/OrderDetailClient";
import Link from "next/link";

type Params = { id: string };

export default async function OrderDetailPage({ params }: { params: Promise<Params> }) {
  const { id } = await params;

  let dto;
  try {
    dto = await getOrderServer(id);
  } catch (err) {
    const status = (err as { status?: number }).status;

    if (status === 401 || status === 403) {
      return (
        <div className="container mx-auto px-4 py-12 max-w-lg space-y-3">
          <h1 className="text-2xl font-semibold">You have been signed out</h1>
          <p className="text-muted-foreground">
            Your session has expired or you are not signed in. Please log in
            again to view this order.
          </p>
          <Link
            href={`/login?next=/orders/${id}`}
            className="inline-block underline underline-offset-4 font-medium"
          >
            Sign in
          </Link>
        </div>
      );
    }

    if (status === 404) {
      return (
        <div className="container mx-auto px-4 py-12 max-w-lg space-y-3">
          <h1 className="text-2xl font-semibold">Order not found</h1>
          <p className="text-muted-foreground">
            This order does not exist or you do not have access to it.
          </p>
        </div>
      );
    }

    return (
      <div className="container mx-auto px-4 py-12 max-w-lg space-y-3">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="text-muted-foreground">
          Unable to load the order. Please try again later or contact support.
        </p>
      </div>
    );
  }

  const vm = mapOrderToVm(dto);

  return (
    <div className="space-y-6">
      <OrderDetailClient order={vm} />
    </div>
  );
}

