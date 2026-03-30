import pytest
from django.contrib import admin, messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from orders.models import Order
from shipping.admin import ShipmentAdmin, ShipmentEventAdmin
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


@pytest.fixture
def shipment_event_admin():
    return ShipmentEventAdmin(ShipmentEvent, AdminSite())


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
def test_admin_action_simulate_failed_delivery_updates_mock_shipment(shipment_admin):
    user = User.objects.create_user(email="admin-shipment-failed@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    ShipmentEventService.simulate_admin_event(
        shipment=shipment,
        normalized_status=ShipmentStatus.IN_TRANSIT,
    )
    request = _request_with_messages()

    shipment_admin.simulate_failed_delivery(request, Shipment.objects.filter(pk=shipment.pk))

    shipment.refresh_from_db()
    order.refresh_from_db()

    assert shipment.status == ShipmentStatus.FAILED_DELIVERY
    assert order.status == Order.Status.DELIVERY_FAILED
    assert ShipmentEvent.objects.filter(shipment=shipment, normalized_status=ShipmentStatus.FAILED_DELIVERY).count() == 1
    stored = list(messages.get_messages(request))
    assert any("simulated failed_delivery" in str(message).lower() for message in stored)


@pytest.mark.django_db
def test_admin_action_retry_failed_delivery_creates_new_shipment(shipment_admin):
    user = User.objects.create_user(email="admin-shipment-retry@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    failed_shipment = ShipmentService.create_for_paid_order(order=order)
    ShipmentEventService.simulate_admin_event(
        shipment=failed_shipment,
        normalized_status=ShipmentStatus.IN_TRANSIT,
    )
    ShipmentEventService.simulate_admin_event(
        shipment=failed_shipment,
        normalized_status=ShipmentStatus.FAILED_DELIVERY,
    )
    request = _request_with_messages()

    shipment_admin.retry_failed_delivery(request, Shipment.objects.filter(pk=failed_shipment.pk))

    failed_shipment.refresh_from_db()
    order.refresh_from_db()
    current_shipment = order.get_current_shipment()
    stored = list(messages.get_messages(request))

    assert Shipment.objects.filter(order=order).count() == 2
    assert failed_shipment.status == ShipmentStatus.FAILED_DELIVERY
    assert current_shipment is not None
    assert current_shipment.pk != failed_shipment.pk
    assert current_shipment.status == ShipmentStatus.LABEL_CREATED
    assert len(stored) == 1
    assert str(stored[0]) == "Retry failed delivery: 1 orders updated."


@pytest.mark.django_db
def test_shipment_admin_exposes_operations_summary_links_and_grouped_fieldsets(shipment_admin):
    user = User.objects.create_user(email="admin-shipment-summary@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)

    assert shipment_admin.shipment_status_label(shipment) == "Label created"
    assert shipment_admin.shipping_service_summary(shipment) == "MOCK / Standard"
    assert "Order #" in str(shipment_admin.order_summary(shipment))
    assert "Open order" in str(shipment_admin.order_admin_link(shipment))
    assert "Open label" in str(shipment_admin.label_asset_link(shipment))
    assert "Open public tracking" in str(shipment_admin.public_tracking_link(shipment))
    assert "Public tracking" in str(shipment_admin.operations_links(shipment))

    fieldsets = dict(shipment_admin.get_fieldsets(RequestFactory().get("/admin/shipping/shipment/1/change/"), shipment))

    assert "Operations summary" in fieldsets
    assert "Shipment timeline" in fieldsets
    assert "Receiver details" in fieldsets
    assert fieldsets["Technical details"]["classes"] == ("collapse",)
    assert "meta_pretty" in fieldsets["Technical details"]["fields"]


@pytest.mark.django_db
def test_shipment_event_admin_exposes_readable_summary_and_secondary_payload(shipment_event_admin):
    user = User.objects.create_user(email="admin-shipment-event@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = ShipmentService.create_for_paid_order(order=order)
    event = ShipmentEvent.objects.create(
        shipment=shipment,
        event_type="tracking_updated",
        raw_status="FAILED_DELIVERY",
        normalized_status=ShipmentStatus.FAILED_DELIVERY,
        external_event_id="evt-123",
        payload={"source": "admin_simulation", "status": "FAILED_DELIVERY"},
    )

    assert shipment_event_admin.event_summary(event) == "Tracking Updated"
    assert shipment_event_admin.source_summary(event) == "Admin Simulation"
    assert shipment_event_admin.normalized_status_label(event) == "Failed delivery"
    assert "Shipment #" in str(shipment_event_admin.shipment_admin_link(event))
    assert "Order #" in str(shipment_event_admin.order_admin_link(event))
    assert "admin_simulation" in str(shipment_event_admin.payload_pretty(event))

    fieldsets = dict(shipment_event_admin.get_fieldsets(RequestFactory().get("/admin/shipping/shipmentevent/1/change/"), event))

    assert "Event summary" in fieldsets
    assert fieldsets["Technical details"]["classes"] == ("collapse",)
    assert "payload_pretty" in fieldsets["Technical details"]["fields"]


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