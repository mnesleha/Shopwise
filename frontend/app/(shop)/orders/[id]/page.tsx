import { getOrderServer } from "@/lib/server/orders";
import { mapOrderToVm } from "@/lib/mappers/orders";
import OrderDetailClient from "@/components/order/OrderDetailClient";

type Params = { id: string };

export default async function OrderDetailPage({ params }: { params: Promise<Params> }) {
  const { id } = await params;

  const dto = await getOrderServer(id);
  const vm = mapOrderToVm(dto);

  return (
    <div className="space-y-6">
      <OrderDetailClient order={vm} />
    </div>
  );
}
