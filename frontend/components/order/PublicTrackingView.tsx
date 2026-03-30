import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PublicTrackingViewModel } from "@/lib/mappers/tracking";

function getShipmentStatusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  const normalized = status.toUpperCase();
  if (normalized === "DELIVERED") return "default";
  if (
    normalized === "IN_TRANSIT" ||
    normalized === "LABEL_CREATED" ||
    normalized === "FAILED_DELIVERY"
  ) {
    return "secondary";
  }
  if (normalized === "CANCELLED") {
    return "destructive";
  }
  return "outline";
}

function getShipmentStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    PENDING: "Pending",
    LABEL_CREATED: "Label created",
    IN_TRANSIT: "In transit",
    DELIVERED: "Delivered",
    FAILED_DELIVERY: "Delayed",
    CANCELLED: "Cancelled",
  };
  return labels[status.toUpperCase()] || status;
}

function hasDeliveryIssue(status: string): boolean {
  return status.toUpperCase() === "FAILED_DELIVERY";
}

function formatShipmentTimelineTime(value?: string | null): string {
  if (!value) return "Time pending";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Time pending";
  }

  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hours = String(date.getUTCHours()).padStart(2, "0");
  const minutes = String(date.getUTCMinutes()).padStart(2, "0");

  return `${year}-${month}-${day} ${hours}:${minutes} UTC`;
}

export default function PublicTrackingView({
  tracking,
}: {
  tracking: PublicTrackingViewModel;
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Shipment summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground">Tracking number</span>
            <span className="font-medium text-foreground">
              {tracking.trackingNumber}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-muted-foreground">Status</span>
            <div>
              <Badge variant={getShipmentStatusBadgeVariant(tracking.status)}>
                {getShipmentStatusLabel(tracking.status)}
              </Badge>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <span className="text-muted-foreground">Carrier</span>
              <span className="font-medium text-foreground">
                {tracking.carrierName}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-muted-foreground">Service</span>
              <span className="font-medium text-foreground">
                {tracking.serviceName}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Shipment timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            {tracking.shipmentTimeline.map((item, index) => {
              const isLast = index === tracking.shipmentTimeline.length - 1;
              const isDelayedCurrentStep =
                hasDeliveryIssue(tracking.status) &&
                item.isCurrent &&
                item.status.toUpperCase() === "IN_TRANSIT";
              const visibleLabel = isDelayedCurrentStep
                ? "Delayed (In transit)"
                : item.label;
              return (
                <div
                  key={`${item.status}-${item.occurredAt ?? index}`}
                  className="flex gap-3"
                >
                  <div className="flex flex-col items-center">
                    <span
                      className={[
                        "mt-1 h-2.5 w-2.5 rounded-full border",
                        item.isCurrent
                          ? "border-foreground bg-foreground"
                          : "border-border bg-background",
                      ].join(" ")}
                    />
                    {!isLast && <span className="mt-1 h-full w-px bg-border" />}
                  </div>
                  <div className="pb-4">
                    <div
                      className={[
                        "flex flex-wrap items-center gap-2",
                        isDelayedCurrentStep
                          ? "mb-2 rounded-2xl border border-amber-300/80 bg-amber-50 px-3 py-3"
                          : "",
                      ].join(" ")}
                    >
                      <p className="font-medium text-foreground">
                        {visibleLabel}
                      </p>
                      {item.isCurrent && !isDelayedCurrentStep && (
                        <Badge variant="secondary">Current</Badge>
                      )}
                      {isDelayedCurrentStep && (
                        <p className="basis-full text-[11px] leading-tight text-amber-950">
                          We're arranging a new delivery attempt.
                        </p>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {formatShipmentTimelineTime(item.occurredAt)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
