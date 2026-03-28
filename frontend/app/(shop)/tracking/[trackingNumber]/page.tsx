import PublicTrackingView from "@/components/order/PublicTrackingView";
import { mapPublicTrackingToVm } from "@/lib/mappers/tracking";
import { getPublicTrackingServer } from "@/lib/server/tracking";

type Params = { trackingNumber: string };

export default async function PublicTrackingPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { trackingNumber } = await params;

  let dto;
  try {
    dto = await getPublicTrackingServer(trackingNumber);
  } catch (err) {
    const status = (err as { status?: number }).status;

    if (status === 404) {
      return (
        <div className="container mx-auto max-w-2xl px-4 py-12 space-y-3">
          <h1 className="text-2xl font-semibold">Tracking number not found</h1>
          <p className="text-muted-foreground">
            No shipment is available for this tracking number.
          </p>
        </div>
      );
    }

    return (
      <div className="container mx-auto max-w-2xl px-4 py-12 space-y-3">
        <h1 className="text-2xl font-semibold">Unable to load tracking</h1>
        <p className="text-muted-foreground">Please try again later.</p>
      </div>
    );
  }

  const tracking = mapPublicTrackingToVm(dto);

  return (
    <div className="container mx-auto max-w-5xl px-4 py-12 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Track shipment</h1>
        <p className="text-muted-foreground">
          Public shipment milestones for tracking number {tracking.trackingNumber}.
        </p>
      </div>
      <PublicTrackingView tracking={tracking} />
    </div>
  );
}