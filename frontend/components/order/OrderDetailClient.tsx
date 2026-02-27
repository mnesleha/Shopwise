"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  OrderDetail,
  type OrderViewModel,
} from "@/components/order/OrderDetail";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function OrderDetailClient({
  order,
}: {
  order: OrderViewModel;
}) {
  const router = useRouter();
  const [orderVm, setOrderVm] = React.useState(order);
  const [open, setOpen] = React.useState(false);
  const [isCancelling, setIsCancelling] = React.useState(false);

  const canCancel = orderVm.status === "CREATED";

  type CancelOrderResponseDto = {
    id: number | string;
    status: string;
    total: string;
    cancel_reason?: string;
    cancelled_by?: string;
    cancelled_at?: string;
    items: Array<{
      id: number | string;
      product: number | string;
      quantity: number;
      unit_price: string;
      line_total: string;
      discount: null | { type: string; value: string };
    }>;
  };

  type ApiErrorDto = { code?: string; message?: string };

  async function confirmCancel() {
    if (!canCancel) return;

    setIsCancelling(true);
    try {
      // IMPORTANT: no leading "/" so axios baseURL (/api/v1) is applied
      const res = await api.post<CancelOrderResponseDto>(
        `orders/${orderVm.id}/cancel/`,
      );

      // Update UI immediately (use server snapshot status)
      setOrderVm((prev) => ({
        ...prev,
        status: res.data.status as any,
      }));

      toast.success("Order cancelled");
      setOpen(false);

      // Revalidate SSR segments (header, etc.)
      router.refresh();
    } catch (e: any) {
      const status = e?.response?.status;
      const data = e?.response?.data as ApiErrorDto | undefined;

      if (status === 409 && data?.message) {
        toast.error(data.message);
      } else {
        toast.error("Cancellation failed. Please try again.");
      }
    } finally {
      setIsCancelling(false);
    }
  }

  return (
    <OrderDetail
      order={orderVm}
      onBackToShop={() => router.push("/products")}
      onPrint={() => window.print()}
      onDownloadPdf={undefined}
      headerActions={
        canCancel ? (
          <>
            <Button variant="destructive" onClick={() => setOpen(true)}>
              Cancel order
            </Button>

            <AlertDialog open={open} onOpenChange={setOpen}>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Cancel this order?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will cancel your order. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={isCancelling}>
                    Keep order
                  </AlertDialogCancel>
                  <AlertDialogAction
                    disabled={isCancelling}
                    onClick={(evt) => {
                      // Prevent auto-close; we close only on success.
                      evt.preventDefault();
                      void confirmCancel();
                    }}
                  >
                    {isCancelling ? "Cancelling..." : "Cancel order"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        ) : null
      }
    />
  );
}
