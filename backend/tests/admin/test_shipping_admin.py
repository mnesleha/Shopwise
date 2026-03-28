import pytest
from django.contrib import admin, messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from orders.models import Order
from shipping.admin import ShipmentAdmin
from shipping.models import Shipment, ShipmentEvent
from shipping.services.events import ShipmentEventService
from shipping.services.shipment import ShipmentService
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order

User = get_user_model()


def _request_with_messages():
    request = RequestFactory().post("/admin/shipping/shipment/")
    request.session = {}
    request.user = User()
    request._messages = FallbackStorage(request)
    return request


@pytest.fixture
def shipment_admin():
    return ShipmentAdmin(Shipment, AdminSite())


@pytest.mark.django_db
def test_admin_action_simulate_in_transit_updates_mock_shipment(shipment_admin):
    user = User.objects.create_user(email="admin-shipment-action@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    request = _request_with_messages()

    shipment_admin.simulate_in_transit(request, Shipment.objects.filter(pk=shipment.pk))

    shipment.refresh_from_db()
    order.refresh_from_db()

    assert shipment.status == ShipmentStatus.IN_TRANSIT
    assert order.status == Order.Status.SHIPPED
    assert ShipmentEvent.objects.filter(shipment=shipment, normalized_status=ShipmentStatus.IN_TRANSIT).count() == 1
    stored = list(messages.get_messages(request))
    assert any("simulated in_transit" in str(message).lower() for message in stored)


@pytest.mark.django_db
def test_admin_action_uses_shipment_event_service(monkeypatch, shipment_admin):
    user = User.objects.create_user(email="admin-shipment-service@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    request = _request_with_messages()
    calls = []

    def fake_simulate_admin_event(*, shipment, normalized_status):
        calls.append((shipment.pk, normalized_status))
        return None

    monkeypatch.setattr(
        ShipmentEventService,
        "simulate_admin_event",
        fake_simulate_admin_event,
    )

    shipment_admin.simulate_delivered(request, Shipment.objects.filter(pk=shipment.pk))

    shipment.refresh_from_db()
    order.refresh_from_db()

    assert calls == [(shipment.pk, ShipmentStatus.DELIVERED)]
    assert shipment.status == ShipmentStatus.LABEL_CREATED
    assert order.status == Order.Status.PAID


@pytest.mark.django_db
def test_admin_action_rejects_non_supported_provider(shipment_admin):
    user = User.objects.create_user(email="admin-shipment-invalid@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = Shipment.objects.create(
        order=order,
        provider_code="UPS",
        service_code="standard",
        carrier_name_snapshot="Carrier",
        service_name_snapshot="Standard",
        status=ShipmentStatus.LABEL_CREATED,
    )
    request = _request_with_messages()

    shipment_admin.simulate_in_transit(request, Shipment.objects.filter(pk=shipment.pk))

    shipment.refresh_from_db()
    order.refresh_from_db()

    assert shipment.status == ShipmentStatus.LABEL_CREATED
    assert order.status == Order.Status.PAID
    assert ShipmentEvent.objects.filter(shipment=shipment).count() == 0
    stored = list(messages.get_messages(request))
    assert any("not available for this provider" in str(message).lower() for message in stored)