import pytest
from django.contrib.auth import get_user_model

from shipping.models import Shipment, ShipmentEvent
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_shipment_defaults_and_relation_to_order():
    user = User.objects.create_user(email="shipping-model@example.com", password="pass")
    order = create_valid_order(user=user)

    shipment = Shipment.objects.create(
        order=order,
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Carrier",
        service_name_snapshot="Standard",
    )

    assert shipment.order == order
    assert shipment.status == ShipmentStatus.PENDING
    assert shipment.receiver_snapshot == {}
    assert shipment.meta == {}
    assert str(shipment) == f"Shipment #{shipment.pk} ({ShipmentStatus.PENDING})"


def test_shipment_event_stores_normalized_status_and_payload():
    user = User.objects.create_user(email="shipping-event@example.com", password="pass")
    order = create_valid_order(user=user)
    shipment = Shipment.objects.create(
        order=order,
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Carrier",
        service_name_snapshot="Express",
        tracking_number="MOCK-1-EXPRESS",
    )

    event = ShipmentEvent.objects.create(
        shipment=shipment,
        event_type="status_update",
        raw_status="DELIVERED",
        normalized_status=ShipmentStatus.DELIVERED,
        payload={"status": "DELIVERED"},
        external_event_id="evt-1",
    )

    assert event.shipment == shipment
    assert event.normalized_status == ShipmentStatus.DELIVERED
    assert event.payload == {"status": "DELIVERED"}
    assert str(event) == f"ShipmentEvent #{event.pk} (status_update)"