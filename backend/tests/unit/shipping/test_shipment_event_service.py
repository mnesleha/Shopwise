from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware

from orders.models import Order
from shipping.models import ShipmentEvent
from shipping.providers.base import ParsedWebhookEvent
from shipping.services.events import ShipmentEventService
from shipping.services.shipment import ShipmentService
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order

User = get_user_model()


@pytest.mark.django_db
def test_process_in_transit_event_persists_event_and_updates_shipment_and_order():
    user = User.objects.create_user(email="ship-event-transit@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    occurred_at = make_aware(datetime(2026, 3, 28, 16, 0, 0))

    event = ShipmentEventService.process_event(
        shipment=shipment,
        event=ParsedWebhookEvent(
            event_type="tracking_updated",
            normalized_status=ShipmentStatus.IN_TRANSIT,
            raw_status="IN_TRANSIT",
            external_event_id="evt-in-transit-1",
            occurred_at=occurred_at,
            payload={"status": "IN_TRANSIT"},
        ),
    )

    shipment.refresh_from_db()
    order.refresh_from_db()

    assert ShipmentEvent.objects.count() == 1
    assert event.normalized_status == ShipmentStatus.IN_TRANSIT
    assert shipment.status == ShipmentStatus.IN_TRANSIT
    assert shipment.shipped_at == occurred_at
    assert order.status == Order.Status.SHIPPED


@pytest.mark.django_db
def test_process_delivered_event_updates_shipment_and_order():
    user = User.objects.create_user(email="ship-event-delivered@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    occurred_at = make_aware(datetime(2026, 3, 28, 17, 30, 0))

    ShipmentEventService.process_event(
        shipment=shipment,
        event=ParsedWebhookEvent(
            event_type="tracking_updated",
            normalized_status=ShipmentStatus.DELIVERED,
            raw_status="DELIVERED",
            external_event_id="evt-delivered-1",
            occurred_at=occurred_at,
            payload={"status": "DELIVERED"},
        ),
    )

    shipment.refresh_from_db()
    order.refresh_from_db()

    assert shipment.status == ShipmentStatus.DELIVERED
    assert shipment.shipped_at == occurred_at
    assert shipment.delivered_at == occurred_at
    assert order.status == Order.Status.DELIVERED


@pytest.mark.django_db
def test_duplicate_event_is_idempotent():
    user = User.objects.create_user(email="ship-event-idem@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    occurred_at = make_aware(datetime(2026, 3, 28, 18, 0, 0))
    event = ParsedWebhookEvent(
        event_type="tracking_updated",
        normalized_status=ShipmentStatus.IN_TRANSIT,
        raw_status="IN_TRANSIT",
        external_event_id="evt-idem-1",
        occurred_at=occurred_at,
        payload={"status": "IN_TRANSIT"},
    )

    first = ShipmentEventService.process_event(shipment=shipment, event=event)
    second = ShipmentEventService.process_event(shipment=shipment, event=event)

    shipment.refresh_from_db()

    assert first.pk == second.pk
    assert ShipmentEvent.objects.filter(shipment=shipment).count() == 1
    assert shipment.status == ShipmentStatus.IN_TRANSIT


@pytest.mark.django_db
def test_event_without_external_id_and_occurred_at_is_not_falsely_deduplicated():
    user = User.objects.create_user(email="ship-event-noid-notime@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)

    first = ShipmentEventService.process_event(
        shipment=shipment,
        event=ParsedWebhookEvent(
            event_type="tracking_updated",
            normalized_status=ShipmentStatus.IN_TRANSIT,
            raw_status="IN_TRANSIT",
            payload={"status": "IN_TRANSIT", "sequence": 1},
        ),
    )
    second = ShipmentEventService.process_event(
        shipment=shipment,
        event=ParsedWebhookEvent(
            event_type="tracking_updated",
            normalized_status=ShipmentStatus.IN_TRANSIT,
            raw_status="IN_TRANSIT",
            payload={"status": "IN_TRANSIT", "sequence": 2},
        ),
    )

    assert first.pk != second.pk
    assert ShipmentEvent.objects.filter(shipment=shipment).count() == 2


@pytest.mark.django_db
def test_event_without_external_id_but_with_occurred_at_uses_fallback_dedup():
    user = User.objects.create_user(email="ship-event-notime-fallback@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    occurred_at = make_aware(datetime(2026, 3, 28, 19, 0, 0))
    event = ParsedWebhookEvent(
        event_type="tracking_updated",
        normalized_status=ShipmentStatus.IN_TRANSIT,
        raw_status="IN_TRANSIT",
        occurred_at=occurred_at,
        payload={"status": "IN_TRANSIT"},
    )

    first = ShipmentEventService.process_event(shipment=shipment, event=event)
    second = ShipmentEventService.process_event(shipment=shipment, event=event)

    assert first.pk == second.pk
    assert ShipmentEvent.objects.filter(shipment=shipment).count() == 1
