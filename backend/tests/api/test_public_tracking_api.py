import pytest

from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order


pytestmark = pytest.mark.django_db


def test_public_tracking_returns_safe_shipment_summary(client):
    order = create_valid_order(user=None, customer_email="guest@example.com")
    shipment = order.shipments.create(
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Express",
        tracking_number="MOCK-TRACK-123",
        status=ShipmentStatus.IN_TRANSIT,
        receiver_snapshot={"name": "Guest User"},
    )
    shipment.events.create(
        event_type="status_update",
        raw_status="IN_TRANSIT",
        normalized_status=ShipmentStatus.IN_TRANSIT,
        payload={"status": "IN_TRANSIT", "internal": "hidden"},
    )

    response = client.get("/api/v1/tracking/MOCK-TRACK-123/")

    assert response.status_code == 200
    assert response.data == {
        "tracking_number": "MOCK-TRACK-123",
        "status": ShipmentStatus.IN_TRANSIT,
        "carrier_name": "Mock Shipping",
        "service_name": "Express",
        "shipment_timeline": response.data["shipment_timeline"],
    }
    assert [entry["status"] for entry in response.data["shipment_timeline"]] == [
        ShipmentStatus.PENDING,
        ShipmentStatus.IN_TRANSIT,
    ]
    assert "customer_email" not in response.data
    assert "payload" not in str(response.data)


def test_public_tracking_returns_404_for_unknown_tracking_number(client):
    response = client.get("/api/v1/tracking/UNKNOWN-TRACKING/")

    assert response.status_code == 404