from __future__ import annotations

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from shipping.providers.base import (
    BaseShippingProvider,
    CreateShipmentContext,
    ParsedWebhookEvent,
    ProviderCreateShipmentResult,
    ShippingServiceOption,
    TrackingStatusResult,
)
from shipping.statuses import ShipmentStatus


class MockShippingProvider(BaseShippingProvider):
    provider_code = "MOCK"
    carrier_name = "Mock Carrier"

    def list_services(self, *, order=None, extra=None) -> list[ShippingServiceOption]:
        return [
            ShippingServiceOption(
                provider_code=self.provider_code,
                service_code="standard",
                carrier_name=self.carrier_name,
                service_name="Standard",
            ),
            ShippingServiceOption(
                provider_code=self.provider_code,
                service_code="express",
                carrier_name=self.carrier_name,
                service_name="Express",
            ),
        ]

    def create_shipment(self, context: CreateShipmentContext) -> ProviderCreateShipmentResult:
        service_name = self._service_name(context.service_code)
        tracking_number = f"MOCK-{context.order.pk}-{context.service_code.upper()}"
        return ProviderCreateShipmentResult(
            provider_code=self.provider_code,
            service_code=context.service_code,
            carrier_name=self.carrier_name,
            service_name=service_name,
            status=ShipmentStatus.LABEL_CREATED,
            tracking_number=tracking_number,
            carrier_reference=f"REF-{tracking_number}",
            label_url=f"https://mock-shipping.local/labels/{tracking_number}",
            receiver_snapshot=dict(context.receiver),
            meta={"mock": True},
        )

    def get_tracking_status(self, *, tracking_number: str, extra=None) -> TrackingStatusResult:
        raw_status = (extra or {}).get("raw_status", "IN_TRANSIT")
        normalized_status = self._normalize_status(raw_status)
        delivered_at = (extra or {}).get("delivered_at")
        if isinstance(delivered_at, str):
            delivered_at = parse_datetime(delivered_at)

        return TrackingStatusResult(
            normalized_status=normalized_status,
            raw_status=raw_status,
            tracking_number=tracking_number,
            delivered_at=delivered_at if normalized_status == ShipmentStatus.DELIVERED else None,
            meta={"mock": True},
        )

    def parse_webhook(self, payload: dict[str, object]) -> ParsedWebhookEvent:
        raw_status = str(payload.get("status", "PENDING"))
        normalized_status = self._normalize_status(raw_status)
        occurred_at_raw = payload.get("occurred_at")
        occurred_at = None
        if isinstance(occurred_at_raw, str):
            occurred_at = parse_datetime(occurred_at_raw)

        return ParsedWebhookEvent(
            event_type=str(payload.get("event_type", "status_update")),
            raw_status=raw_status,
            normalized_status=normalized_status,
            external_event_id=str(payload["event_id"]) if payload.get("event_id") is not None else None,
            occurred_at=occurred_at,
            payload=dict(payload),
        )

    def build_simulated_event(self, *, shipment, normalized_status: str) -> ParsedWebhookEvent:
        normalized_status = self._normalize_status(normalized_status)
        event_key = normalized_status.lower()
        return ParsedWebhookEvent(
            event_type="admin_simulation",
            raw_status=normalized_status,
            normalized_status=normalized_status,
            external_event_id=f"mock-sim:{shipment.pk}:{event_key}",
            occurred_at=timezone.now(),
            payload={
                "source": "admin_simulation",
                "shipment_id": shipment.pk,
                "tracking_number": shipment.tracking_number,
                "status": normalized_status,
            },
        )

    def _service_name(self, service_code: str) -> str:
        if service_code == "express":
            return "Express"
        return "Standard"

    def _normalize_status(self, raw_status: str) -> str:
        normalized = raw_status.strip().upper()
        status_map = {
            "PENDING": ShipmentStatus.PENDING,
            "LABEL_CREATED": ShipmentStatus.LABEL_CREATED,
            "IN_TRANSIT": ShipmentStatus.IN_TRANSIT,
            "DELIVERED": ShipmentStatus.DELIVERED,
            "FAILED_DELIVERY": ShipmentStatus.FAILED_DELIVERY,
            "CANCELLED": ShipmentStatus.CANCELLED,
            "EXCEPTION": ShipmentStatus.FAILED_DELIVERY,
        }
        return status_map.get(normalized, ShipmentStatus.PENDING)