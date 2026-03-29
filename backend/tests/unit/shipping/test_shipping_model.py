import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import override_settings
from django.utils.timezone import now

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


def test_shipment_get_label_url_prefers_storage_asset(tmp_path):
    user = User.objects.create_user(email="shipping-label-url@example.com", password="pass")
    order = create_valid_order(user=user)

    with override_settings(MEDIA_ROOT=str(tmp_path)):
        shipment = Shipment.objects.create(
            order=order,
            provider_code="MOCK",
            service_code="express",
            carrier_name_snapshot="Mock Carrier",
            service_name_snapshot="Express",
            tracking_number="MOCK-1-EXPRESS",
            label_url="https://legacy.example/placeholder.svg",
        )
        shipment.label_file.save("mock-label.svg", ContentFile(b"<svg></svg>"), save=True)

        assert shipment.get_label_url() == shipment.label_file.url


def test_shipment_get_timeline_returns_canonical_milestones():
    user = User.objects.create_user(email="shipping-timeline@example.com", password="pass")
    order = create_valid_order(user=user)
    shipment = Shipment.objects.create(
        order=order,
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Carrier",
        service_name_snapshot="Express",
        tracking_number="MOCK-1-EXPRESS",
        status=ShipmentStatus.IN_TRANSIT,
    )
    created_at = shipment.created_at

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type="status_update",
        raw_status="LABEL_CREATED",
        normalized_status=ShipmentStatus.LABEL_CREATED,
        payload={"status": "LABEL_CREATED"},
        occurred_at=created_at,
        processed_at=created_at,
    )
    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type="status_update",
        raw_status="IN_TRANSIT",
        normalized_status=ShipmentStatus.IN_TRANSIT,
        payload={"status": "IN_TRANSIT"},
        occurred_at=now(),
    )

    timeline = shipment.get_timeline()

    assert [entry["status"] for entry in timeline] == [
        ShipmentStatus.LABEL_CREATED,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.DELIVERED,
    ]
    assert timeline[1]["is_current"] is True
    assert timeline[1]["label"] == "In transit"
    assert timeline[2]["occurred_at"] is None


def test_shipment_get_timeline_keeps_main_progress_for_failed_delivery():
    user = User.objects.create_user(email="shipping-timeline-failed@example.com", password="pass")
    order = create_valid_order(user=user)
    shipment = Shipment.objects.create(
        order=order,
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Carrier",
        service_name_snapshot="Express",
        tracking_number="MOCK-2-EXPRESS",
        status=ShipmentStatus.FAILED_DELIVERY,
    )

    ShipmentEvent.objects.create(
        shipment=shipment,
        event_type="status_update",
        raw_status="IN_TRANSIT",
        normalized_status=ShipmentStatus.IN_TRANSIT,
        payload={"status": "IN_TRANSIT"},
        occurred_at=now(),
    )

    timeline = shipment.get_timeline()

    assert [entry["status"] for entry in timeline] == [
        ShipmentStatus.LABEL_CREATED,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.DELIVERED,
    ]
    assert [entry["is_current"] for entry in timeline] == [False, True, False]