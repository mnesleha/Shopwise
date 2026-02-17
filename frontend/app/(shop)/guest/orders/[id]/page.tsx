import OrderDetailClient from "@/components/order/OrderDetailClient";
import { mapOrderToVm } from "@/lib/mappers/orders";
import { getGuestOrderServer } from "@/lib/server/guest-orders";

type Params = { id: string };
type SearchParams = { token?: string };

export default async function GuestOrderPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<SearchParams>;
}) {
  const { id } = await params;
  const sp = await searchParams;

  const token = sp.token;
  if (!token) {
    // token is required by backend – show a deterministic error
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Order access link invalid</h1>
        <p className="text-muted-foreground">Missing token in URL.</p>
      </div>
    );
  }

  const dto = await getGuestOrderServer(id, token);
  const vm = mapOrderToVm(dto);

  return (
    <div className="container mx-auto px-4 py-8">
      <OrderDetailClient order={vm} />
    </div>
  );
}
