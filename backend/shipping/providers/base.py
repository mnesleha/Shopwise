from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shipping.statuses import ShipmentStatus


@dataclass
class ShippingServiceOption:
    provider_code: str
    service_code: str
    carrier_name: str
    service_name: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CreateShipmentContext:
    order: Any
    service_code: str
    receiver: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderCreateShipmentResult:
    provider_code: str
    service_code: str
    carrier_name: str
    service_name: str
    status: str = ShipmentStatus.PENDING
    tracking_number: str | None = None
    carrier_reference: str | None = None
    label_url: str | None = None
    receiver_snapshot: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackingStatusResult:
    normalized_status: str
    raw_status: str | None = None
    tracking_number: str | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedWebhookEvent:
    event_type: str
    normalized_status: str
    payload: dict[str, Any] = field(default_factory=dict)
    raw_status: str | None = None
    external_event_id: str | None = None
    occurred_at: datetime | None = None


class BaseShippingProvider(ABC):
    provider_code: str

    @abstractmethod
    def list_services(self, *, order: Any | None = None, extra: dict[str, Any] | None = None) -> list[ShippingServiceOption]:
        ...

    @abstractmethod
    def create_shipment(self, context: CreateShipmentContext) -> ProviderCreateShipmentResult:
        ...

    @abstractmethod
    def get_tracking_status(self, *, tracking_number: str, extra: dict[str, Any] | None = None) -> TrackingStatusResult:
        ...

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any]) -> ParsedWebhookEvent:
        ...

    def build_simulated_event(self, *, shipment: Any, normalized_status: str) -> ParsedWebhookEvent:
        raise NotImplementedError("This provider does not support shipment event simulation.")