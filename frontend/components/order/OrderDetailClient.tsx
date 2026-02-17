"use client";

import { useRouter } from "next/navigation";
import { OrderDetail, type OrderViewModel } from "@/components/order/OrderDetail";

export default function OrderDetailClient({ order }: { order: OrderViewModel }) {
  const router = useRouter();

  return (
    <OrderDetail
      order={order}
      onBackToShop={() => router.push("/products")}
      onPrint={() => window.print()}
      onDownloadPdf={undefined}
    />
  );
}
