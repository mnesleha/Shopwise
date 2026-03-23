import OrderDetailClient from "@/components/order/OrderDetailClient";
import GuestAccountBootstrapBanner from "@/components/order/GuestAccountBootstrapBanner";
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

  let dto;
  try {
    dto = await getGuestOrderServer(id, token);
  } catch (err) {
    const status = (err as { status?: number }).status;

    if (status === 404) {
      return (
        <div className="container mx-auto px-4 py-8 space-y-2">
          <h1 className="text-2xl font-semibold">Order not found</h1>
          <p className="text-muted-foreground">
            This order link is no longer valid. If you already created an
            account, you can{" "}
            <a href="/login" className="underline">
              sign in
            </a>{" "}
            and view your orders from your profile.
          </p>
        </div>
      );
    }

    return (
      <div className="container mx-auto px-4 py-8 space-y-2">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="text-muted-foreground">
          Unable to load the order. Please try again later or contact support.
        </p>
      </div>
    );
  }

  const vm = mapOrderToVm(dto);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Account bootstrap / existing-account CTA */}
      <GuestAccountBootstrapBanner
        orderId={dto.id}
        token={token}
        emailAccountExists={dto.email_account_exists}
      />
      <OrderDetailClient order={vm} />
    </div>
  );
}
