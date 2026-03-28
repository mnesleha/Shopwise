import type { ShipmentTimelineEntry } from "@/components/order/OrderDetail";
import type { PublicTrackingDto } from "@/lib/api/tracking";
import { mapShipmentTimeline } from "@/lib/mappers/orders";

export type PublicTrackingViewModel = {
  trackingNumber: string;
  status: string;
  carrierName: string;
  serviceName: string;
  shipmentTimeline: ShipmentTimelineEntry[];
};

export function mapPublicTrackingToVm(
  dto: PublicTrackingDto,
): PublicTrackingViewModel {
  return {
    trackingNumber: dto.tracking_number,
    status: dto.status,
    carrierName: dto.carrier_name,
    serviceName: dto.service_name,
    shipmentTimeline: mapShipmentTimeline(dto.shipment_timeline),
  };
}