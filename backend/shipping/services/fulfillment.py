from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from django.db import transaction

from orders.models import Order
from shipping.models import Shipment
from shipping.providers.resolver import ProviderNotConfiguredException
from shipping.services.eligibility import ShipmentEligibilityService
from shipping.services.events import InvalidShipmentSimulation, ShipmentEventService
from shipping.services.shipment import InvalidShipmentSnapshot, ShipmentService
from shipping.statuses import ShipmentStatus


@dataclass
class BulkOrderFulfillmentResult:
    updated_count: int = 0
    skipped_counts: Counter[str] = field(default_factory=Counter)

    def record_updated(self) -> None:
        self.updated_count += 1

    def record_skipped(self, reason: str) -> None:
        self.skipped_counts[reason] += 1

    def build_message(self, *, action_name: str, reason_labels: dict[str, str]) -> str:
        parts = [f"{action_name}: {self.updated_count} orders updated"]
        for reason, label in reason_labels.items():
            count = self.skipped_counts.get(reason, 0)
            if count:
                parts.append(f"{count} skipped because {label}")
        return "; ".join(parts) + "."


class OrderFulfillmentService:
    @classmethod
    def bulk_create_missing_shipments(cls, *, orders) -> BulkOrderFulfillmentResult:
        return cls._run_bulk(orders=orders, handler=cls.create_missing_shipment_for_order)

    @classmethod
    def bulk_move_current_shipment_to_in_transit(cls, *, orders) -> BulkOrderFulfillmentResult:
        return cls._run_bulk(orders=orders, handler=cls.move_current_shipment_to_in_transit)

    @classmethod
    def bulk_move_current_shipment_to_delivered(cls, *, orders) -> BulkOrderFulfillmentResult:
        return cls._run_bulk(orders=orders, handler=cls.move_current_shipment_to_delivered)

    @classmethod
    def bulk_move_current_shipment_to_failed_delivery(cls, *, orders) -> BulkOrderFulfillmentResult:
        return cls._run_bulk(orders=orders, handler=cls.move_current_shipment_to_failed_delivery)

    @classmethod
    def bulk_retry_failed_delivery(cls, *, orders) -> BulkOrderFulfillmentResult:
        return cls._run_bulk(orders=orders, handler=cls.retry_failed_delivery)

    @classmethod
    def create_missing_shipment_for_order(cls, *, order) -> str:
        with transaction.atomic():
            locked_order = cls._lock_order(order_id=order.pk)
            if not ShipmentEligibilityService.can_create_shipment(order=locked_order):
                return "invalid_order_status"

            if locked_order.get_shipment_count() > 0:
                return "shipment_already_exists"

            try:
                ShipmentService.create_for_order(order=locked_order)
            except InvalidShipmentSnapshot:
                return "invalid_shipping_snapshot"
            except ProviderNotConfiguredException:
                return "provider_not_configured"

            return "updated"

    @classmethod
    def move_current_shipment_to_in_transit(cls, *, order) -> str:
        return cls._move_current_shipment(order=order, expected_status=ShipmentStatus.LABEL_CREATED, next_status=ShipmentStatus.IN_TRANSIT)

    @classmethod
    def move_current_shipment_to_delivered(cls, *, order) -> str:
        return cls._move_current_shipment(order=order, expected_status=ShipmentStatus.IN_TRANSIT, next_status=ShipmentStatus.DELIVERED)

    @classmethod
    def move_current_shipment_to_failed_delivery(cls, *, order) -> str:
        return cls._move_current_shipment(order=order, expected_status=ShipmentStatus.IN_TRANSIT, next_status=ShipmentStatus.FAILED_DELIVERY)

    @classmethod
    def retry_failed_delivery(cls, *, order) -> str:
        with transaction.atomic():
            locked_order = cls._lock_order(order_id=order.pk)
            current_shipment = locked_order.get_current_shipment()
            if current_shipment is None:
                return "no_current_shipment"
            if current_shipment.status != ShipmentStatus.FAILED_DELIVERY:
                return "invalid_shipment_status"

            provider_code = current_shipment.provider_code or locked_order.shipping_provider_code
            service_code = current_shipment.service_code or locked_order.shipping_service_code
            if not provider_code or not service_code:
                return "invalid_shipping_snapshot"

            try:
                ShipmentService.create_retry_for_order(
                    order=locked_order,
                    provider_code=provider_code,
                    service_code=service_code,
                )
            except InvalidShipmentSnapshot:
                return "invalid_shipping_snapshot"
            except ProviderNotConfiguredException:
                return "provider_not_configured"

            return "updated"

    @classmethod
    def _move_current_shipment(cls, *, order, expected_status: str, next_status: str) -> str:
        with transaction.atomic():
            locked_order = cls._lock_order(order_id=order.pk)
            current_shipment = locked_order.get_current_shipment()
            if current_shipment is None:
                return "no_current_shipment"
            if current_shipment.status != expected_status:
                return "invalid_shipment_status"

            try:
                ShipmentEventService.simulate_admin_event(
                    shipment=current_shipment,
                    normalized_status=next_status,
                )
            except InvalidShipmentSimulation:
                return "simulation_unavailable"

            return "updated"

    @classmethod
    def _run_bulk(cls, *, orders, handler) -> BulkOrderFulfillmentResult:
        result = BulkOrderFulfillmentResult()
        for order in orders:
            outcome = handler(order=order)
            if outcome == "updated":
                result.record_updated()
                continue
            result.record_skipped(outcome)
        return result

    @staticmethod
    def _lock_order(*, order_id: int) -> Order:
        locked_order = Order.objects.select_for_update().get(pk=order_id)
        shipments = list(Shipment.objects.select_for_update().filter(order=locked_order))
        locked_order._shipment_summary_shipments_cache = shipments
        locked_order._current_shipment_cache = None
        return locked_order