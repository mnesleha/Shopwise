from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from orders.models import Order
from shipping.models import Shipment, ShipmentEvent
from shipping.providers.base import ParsedWebhookEvent
from shipping.providers.resolver import ProviderNotConfiguredException, resolve_provider
from shipping.statuses import ShipmentStatus


class InvalidShipmentSimulation(ValueError):
    pass


class ShipmentEventService:
    @classmethod
    def process_event(cls, *, shipment, event: ParsedWebhookEvent) -> ShipmentEvent:
        with transaction.atomic():
            locked_shipment = Shipment.objects.select_for_update().select_related("order").get(pk=shipment.pk)

            existing_event = cls._find_existing_event(shipment=locked_shipment, event=event)
            if existing_event is not None:
                return existing_event

            processed_at = timezone.now()
            shipment_event = ShipmentEvent.objects.create(
                shipment=locked_shipment,
                event_type=event.event_type,
                raw_status=event.raw_status,
                normalized_status=event.normalized_status,
                payload=event.payload,
                external_event_id=event.external_event_id,
                occurred_at=event.occurred_at,
                processed_at=processed_at,
            )

            cls._apply_shipment_projection(shipment=locked_shipment, event=event, processed_at=processed_at)
            cls._sync_order_projection(order=locked_shipment.order, shipment=locked_shipment)

            return shipment_event

    @classmethod
    def simulate_admin_event(cls, *, shipment, normalized_status: str) -> ShipmentEvent:
        try:
            provider = resolve_provider(shipment.provider_code)
        except ProviderNotConfiguredException as exc:
            raise InvalidShipmentSimulation(
                "Shipment event simulation is not available for this provider."
            ) from exc

        try:
            event = provider.build_simulated_event(
                shipment=shipment,
                normalized_status=normalized_status,
            )
        except NotImplementedError as exc:
            raise InvalidShipmentSimulation(
                "Shipment event simulation is not available for this provider."
            ) from exc

        return cls.process_event(shipment=shipment, event=event)

    @staticmethod
    def _find_existing_event(*, shipment: Shipment, event: ParsedWebhookEvent) -> ShipmentEvent | None:
        if event.external_event_id:
            return ShipmentEvent.objects.filter(
                shipment=shipment,
                external_event_id=event.external_event_id,
            ).first()

        if event.occurred_at is None:
            return None

        return ShipmentEvent.objects.filter(
            shipment=shipment,
            event_type=event.event_type,
            raw_status=event.raw_status,
            normalized_status=event.normalized_status,
            occurred_at=event.occurred_at,
        ).first()

    @classmethod
    def _apply_shipment_projection(
        cls,
        *,
        shipment: Shipment,
        event: ParsedWebhookEvent,
        processed_at,
    ) -> None:
        next_status = cls._resolve_next_shipment_status(
            current_status=shipment.status,
            incoming_status=event.normalized_status,
        )
        update_fields: list[str] = []

        if next_status != shipment.status:
            shipment.status = next_status
            update_fields.append("status")

        effective_time = event.occurred_at or processed_at
        if next_status == ShipmentStatus.IN_TRANSIT and shipment.shipped_at is None:
            shipment.shipped_at = effective_time
            update_fields.append("shipped_at")

        if next_status == ShipmentStatus.DELIVERED:
            if shipment.shipped_at is None:
                shipment.shipped_at = effective_time
                update_fields.append("shipped_at")
            if shipment.delivered_at is None:
                shipment.delivered_at = effective_time
                update_fields.append("delivered_at")

        if update_fields:
            shipment.save(update_fields=update_fields)

    @staticmethod
    def _resolve_next_shipment_status(*, current_status: str, incoming_status: str) -> str:
        if current_status == ShipmentStatus.DELIVERED and incoming_status != ShipmentStatus.DELIVERED:
            return current_status
        if current_status == ShipmentStatus.CANCELLED and incoming_status != ShipmentStatus.CANCELLED:
            return current_status
        return incoming_status

    @staticmethod
    def _sync_order_projection(*, order: Order, shipment: Shipment) -> None:
        next_status = None

        if shipment.status == ShipmentStatus.LABEL_CREATED and order.status == Order.Status.CREATED:
            next_status = Order.Status.PAID
        elif shipment.status == ShipmentStatus.IN_TRANSIT and order.status in (
            Order.Status.PAID,
            Order.Status.DELIVERY_FAILED,
        ):
            next_status = Order.Status.SHIPPED
        elif shipment.status == ShipmentStatus.DELIVERED and order.status in (
            Order.Status.PAID,
            Order.Status.SHIPPED,
            Order.Status.DELIVERY_FAILED,
        ):
            next_status = Order.Status.DELIVERED
        elif shipment.status == ShipmentStatus.FAILED_DELIVERY and order.status in (
            Order.Status.PAID,
            Order.Status.SHIPPED,
        ):
            next_status = Order.Status.DELIVERY_FAILED

        if next_status and next_status != order.status:
            order.status = next_status
            order.save(update_fields=["status"])