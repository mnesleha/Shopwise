import type { ShipmentTimelineEntryDto } from "@/lib/api/orders";

export type PublicTrackingDto = {
  tracking_number: string;
  status: string;
  carrier_name: string;
  service_name: string;
  shipment_timeline: ShipmentTimelineEntryDto[];
};