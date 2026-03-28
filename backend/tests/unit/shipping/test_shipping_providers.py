import pytest
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime

from shipping.providers.base import CreateShipmentContext
from shipping.providers.mock import MockShippingProvider
from shipping.providers.resolver import (
    ProviderNotConfiguredException,
    resolve_provider,
)
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order

User = get_user_model()


def test_resolve_provider_returns_mock_provider():
    provider = resolve_provider("MOCK")
    assert isinstance(provider, MockShippingProvider)


def test_resolve_provider_raises_for_unknown_provider_code():
    with pytest.raises(ProviderNotConfiguredException):
        resolve_provider("UPS")


def test_mock_provider_lists_foundation_services():
    provider = MockShippingProvider()

    services = provider.list_services()

    assert [service.service_code for service in services] == ["standard", "express"]
    assert all(service.provider_code == "MOCK" for service in services)


@pytest.mark.django_db
def test_mock_provider_create_shipment_returns_normalized_result():
    user = User.objects.create_user(email="shipping-provider@example.com", password="pass")
    order = create_valid_order(user=user)
    provider = MockShippingProvider()

    result = provider.create_shipment(
        CreateShipmentContext(
            order=order,
            service_code="express",
            receiver={
                "first_name": order.shipping_first_name,
                "last_name": order.shipping_last_name,
                "address_line1": order.shipping_address_line1,
                "city": order.shipping_city,
                "postal_code": order.shipping_postal_code,
                "country": order.shipping_country,
                "phone": order.shipping_phone,
            },
        )
    )

    assert result.provider_code == "MOCK"
    assert result.service_code == "express"
    assert result.status == ShipmentStatus.LABEL_CREATED
    assert result.tracking_number == f"MOCK-{order.pk}-EXPRESS"
    assert result.receiver_snapshot["city"] == order.shipping_city


def test_mock_provider_tracking_status_normalizes_delivered_result():
    provider = MockShippingProvider()

    result = provider.get_tracking_status(
        tracking_number="MOCK-10-STANDARD",
        extra={"raw_status": "DELIVERED", "delivered_at": "2026-03-26T10:00:00Z"},
    )

    assert result.tracking_number == "MOCK-10-STANDARD"
    assert result.raw_status == "DELIVERED"
    assert result.normalized_status == ShipmentStatus.DELIVERED
    assert result.delivered_at == parse_datetime("2026-03-26T10:00:00Z")


def test_mock_provider_parse_webhook_normalizes_payload():
    provider = MockShippingProvider()

    event = provider.parse_webhook(
        {
            "event_id": "evt-123",
            "event_type": "tracking_updated",
            "status": "IN_TRANSIT",
            "occurred_at": "2026-03-26T12:34:56Z",
            "tracking_number": "MOCK-10-STANDARD",
        }
    )

    assert event.event_type == "tracking_updated"
    assert event.external_event_id == "evt-123"
    assert event.raw_status == "IN_TRANSIT"
    assert event.normalized_status == ShipmentStatus.IN_TRANSIT
    assert event.payload["tracking_number"] == "MOCK-10-STANDARD"


@pytest.mark.django_db
def test_mock_provider_build_simulated_event_returns_normalized_event():
    user = User.objects.create_user(email="shipping-provider-sim@example.com", password="pass")
    order = create_valid_order(user=user)
    provider = MockShippingProvider()

    result = provider.create_shipment(
        CreateShipmentContext(
            order=order,
            service_code="standard",
            receiver={
                "first_name": order.shipping_first_name,
                "last_name": order.shipping_last_name,
                "address_line1": order.shipping_address_line1,
                "city": order.shipping_city,
                "postal_code": order.shipping_postal_code,
                "country": order.shipping_country,
                "phone": order.shipping_phone,
            },
        )
    )
    shipment = order.shipments.create(
        provider_code=result.provider_code,
        service_code=result.service_code,
        carrier_name_snapshot=result.carrier_name,
        service_name_snapshot=result.service_name,
        tracking_number=result.tracking_number,
        carrier_reference=result.carrier_reference,
        status=result.status,
        label_url=result.label_url,
        receiver_snapshot=result.receiver_snapshot,
        meta=result.meta,
    )

    event = provider.build_simulated_event(
        shipment=shipment,
        normalized_status=ShipmentStatus.DELIVERED,
    )

    assert event.event_type == "admin_simulation"
    assert event.external_event_id == f"mock-sim:{shipment.pk}:delivered"
    assert event.raw_status == ShipmentStatus.DELIVERED
    assert event.normalized_status == ShipmentStatus.DELIVERED
    assert event.payload["shipment_id"] == shipment.pk