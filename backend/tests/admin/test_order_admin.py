import pytest
from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory

from orderitems.admin import (
    CurrentShipmentStatusFilter,
    HasLabelFilter,
    HasShipmentFilter,
    HasTrackingNumberFilter,
    OrderWithItemsAdmin,
    ShippingExceptionFilter,
    ShippingMethodFilter,
    ShippingProviderFilter,
)
from orders.models import Order
from shipping.models import Shipment
from shipping.services.fulfillment import BulkOrderFulfillmentResult, OrderFulfillmentService
from shipping.services.shipment import ShipmentService
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order


pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def order_admin():
    return OrderWithItemsAdmin(Order, AdminSite())


def _filter_queryset(filter_class, value, queryset, order_admin):
    request = RequestFactory().get(
        "/admin/orders/order/",
        {filter_class.parameter_name: value},
    )
    admin_filter = filter_class(
        request,
        request.GET.copy(),
        Order,
        order_admin,
    )
    filtered = admin_filter.queryset(request, queryset)
    return filtered if filtered is not None else queryset


def _request_with_messages():
    request = RequestFactory().post("/admin/orders/order/")
    request.session = {}
    request.user = User()
    request._messages = FallbackStorage(request)
    return request


def test_order_current_shipment_prefers_latest_non_terminal_shipment():
    user = User.objects.create_user(email="order-admin-current@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.SHIPPED)
    in_transit = order.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="TRACK-IN-TRANSIT",
        status=ShipmentStatus.IN_TRANSIT,
    )
    latest_delivered = order.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="TRACK-DELIVERED",
        status=ShipmentStatus.DELIVERED,
    )

    current = order.get_current_shipment()

    assert current == in_transit
    assert current != latest_delivered


def test_order_current_shipment_falls_back_to_latest_terminal_shipment():
    user = User.objects.create_user(email="order-admin-terminal@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.DELIVERED)
    order.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="TRACK-CANCELLED",
        status=ShipmentStatus.CANCELLED,
    )
    failed_delivery = order.shipments.create(
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Express",
        tracking_number="TRACK-FAILED",
        status=ShipmentStatus.FAILED_DELIVERY,
    )

    assert order.get_current_shipment() == failed_delivery


def test_order_admin_exposes_current_shipment_summary_and_links(order_admin):
    user = User.objects.create_user(email="order-admin-visibility@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    shipment = order.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="MOCK-243-STANDARD",
        status=ShipmentStatus.LABEL_CREATED,
        label_url="/media/shipping/labels/mock-243-standard.svg",
    )

    assert order_admin.current_shipment_status(order) == "Label created"
    assert order_admin.current_shipping_method(order) == "Standard"
    assert order_admin.current_shipping_provider(order) == "MOCK"
    assert order_admin.current_tracking_number(order) == "MOCK-243-STANDARD"
    assert order_admin.shipment_count(order) == 1
    assert "Open shipment" in str(order_admin.shipping_links(order))
    assert "Open label" in str(order_admin.shipping_links(order))
    assert str(shipment.pk) in str(order_admin.current_shipment_detail_link(order))
    assert "/tracking/MOCK-243-STANDARD" in str(order_admin.current_public_tracking_link(order))


def test_order_admin_fieldsets_include_current_shipment_summary(order_admin):
    request = RequestFactory().get("/admin/orders/order/1/change/")

    fieldsets = order_admin.get_fieldsets(request)

    assert any(title == "Current shipment summary" for title, _ in fieldsets)


def test_order_admin_fieldsets_only_include_editable_model_fields(order_admin):
    request = RequestFactory().get("/admin/orders/order/1/change/")

    fieldsets = dict(order_admin.get_fieldsets(request))
    base_fields = fieldsets[None]["fields"]

    assert "created_at" in base_fields
    assert "id" not in base_fields


def test_current_shipment_status_filter_supports_no_shipment_and_failed_delivery(order_admin):
    user = User.objects.create_user(email="order-admin-status-filter@example.com", password="pass")
    no_shipment_order = create_valid_order(user=user, status=Order.Status.PAID)
    failed_delivery_order = create_valid_order(user=user, status=Order.Status.SHIPPED)
    failed_delivery_order.shipments.create(
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Express",
        tracking_number="TRACK-FAILED-1",
        status=ShipmentStatus.FAILED_DELIVERY,
    )

    queryset = order_admin.get_queryset(RequestFactory().get("/admin/orders/order/"))

    no_shipment_result = _filter_queryset(
        CurrentShipmentStatusFilter,
        "no_shipment",
        queryset,
        order_admin,
    )
    failed_delivery_result = _filter_queryset(
        CurrentShipmentStatusFilter,
        ShipmentStatus.FAILED_DELIVERY,
        queryset,
        order_admin,
    )

    assert list(no_shipment_result) == [no_shipment_order]
    assert list(failed_delivery_result) == [failed_delivery_order]


def test_shipping_provider_and_method_filters_use_current_shipment(order_admin):
    user = User.objects.create_user(email="order-admin-provider-filter@example.com", password="pass")
    current_order = create_valid_order(user=user, status=Order.Status.SHIPPED)
    current_order.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="TRACK-OLD-DELIVERED",
        status=ShipmentStatus.DELIVERED,
    )
    current_order.shipments.create(
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Express",
        tracking_number="TRACK-CURRENT-EXPRESS",
        status=ShipmentStatus.IN_TRANSIT,
    )
    other_order = create_valid_order(user=user, status=Order.Status.SHIPPED)
    other_order.shipments.create(
        provider_code="ALT",
        service_code="economy",
        carrier_name_snapshot="Alt Shipping",
        service_name_snapshot="Economy",
        tracking_number="TRACK-ALT-1",
        status=ShipmentStatus.IN_TRANSIT,
    )

    queryset = order_admin.get_queryset(RequestFactory().get("/admin/orders/order/"))

    provider_result = _filter_queryset(
        ShippingProviderFilter,
        "MOCK",
        queryset,
        order_admin,
    )
    method_result = _filter_queryset(
        ShippingMethodFilter,
        "Express",
        queryset,
        order_admin,
    )

    assert list(provider_result) == [current_order]
    assert list(method_result) == [current_order]


def test_shipment_presence_and_exception_filters(order_admin):
    user = User.objects.create_user(email="order-admin-exception-filter@example.com", password="pass")
    paid_without_shipment = create_valid_order(user=user, status=Order.Status.PAID)
    missing_label = create_valid_order(user=user, status=Order.Status.SHIPPED)
    missing_label.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="TRACK-NO-LABEL",
        status=ShipmentStatus.LABEL_CREATED,
    )
    missing_tracking = create_valid_order(user=user, status=Order.Status.SHIPPED)
    missing_tracking.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="",
        label_url="/media/shipping/labels/missing-tracking.svg",
        status=ShipmentStatus.LABEL_CREATED,
    )
    multiple_shipments = create_valid_order(user=user, status=Order.Status.SHIPPED)
    multiple_shipments.shipments.create(
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Standard",
        tracking_number="TRACK-1",
        status=ShipmentStatus.CANCELLED,
    )
    multiple_shipments.shipments.create(
        provider_code="MOCK",
        service_code="express",
        carrier_name_snapshot="Mock Shipping",
        service_name_snapshot="Express",
        tracking_number="TRACK-2",
        label_url="/media/shipping/labels/track-2.svg",
        status=ShipmentStatus.IN_TRANSIT,
    )

    queryset = order_admin.get_queryset(RequestFactory().get("/admin/orders/order/"))

    has_shipment_no = _filter_queryset(HasShipmentFilter, "no", queryset, order_admin)
    has_label_no = _filter_queryset(HasLabelFilter, "no", queryset, order_admin)
    has_tracking_no = _filter_queryset(HasTrackingNumberFilter, "no", queryset, order_admin)
    paid_without_shipment_result = _filter_queryset(
        ShippingExceptionFilter,
        "paid_without_shipment",
        queryset,
        order_admin,
    )
    shipment_without_label_result = _filter_queryset(
        ShippingExceptionFilter,
        "shipment_without_label",
        queryset,
        order_admin,
    )
    shipment_without_tracking_result = _filter_queryset(
        ShippingExceptionFilter,
        "shipment_without_tracking",
        queryset,
        order_admin,
    )
    multiple_shipments_result = _filter_queryset(
        ShippingExceptionFilter,
        "multiple_shipments",
        queryset,
        order_admin,
    )

    assert list(has_shipment_no) == [paid_without_shipment]
    assert {order.pk for order in has_label_no} == {
        missing_label.pk,
        paid_without_shipment.pk,
    }
    assert {order.pk for order in has_tracking_no} == {
        missing_tracking.pk,
        paid_without_shipment.pk,
    }
    assert list(paid_without_shipment_result) == [paid_without_shipment]
    assert list(shipment_without_label_result) == [missing_label]
    assert list(shipment_without_tracking_result) == [missing_tracking]
    assert list(multiple_shipments_result) == [multiple_shipments]


def test_order_admin_create_missing_shipment_action_reports_meaningful_counts(order_admin):
    user = User.objects.create_user(email="order-admin-action-create@example.com", password="pass")
    paid_without_shipment = create_valid_order(user=user, status=Order.Status.PAID)
    not_paid_order = create_valid_order(user=user, status=Order.Status.CREATED)
    existing_shipment_order = create_valid_order(user=user, status=Order.Status.PAID)
    ShipmentService.create_for_paid_order(order=existing_shipment_order)
    request = _request_with_messages()

    order_admin.create_missing_shipment(
        request,
        Order.objects.filter(
            pk__in=[paid_without_shipment.pk, not_paid_order.pk, existing_shipment_order.pk],
        ).order_by("pk"),
    )

    paid_without_shipment.refresh_from_db()
    not_paid_order.refresh_from_db()
    existing_shipment_order.refresh_from_db()

    assert Shipment.objects.filter(order=paid_without_shipment).count() == 1
    assert paid_without_shipment.get_current_shipment() is not None
    assert Shipment.objects.filter(order=not_paid_order).count() == 0
    assert Shipment.objects.filter(order=existing_shipment_order).count() == 1

    stored = list(messages.get_messages(request))
    assert len(stored) == 1
    assert str(stored[0]) == (
        "Create missing shipment: 1 orders updated; "
        "1 skipped because order is not PAID; "
        "1 skipped because shipment already exists."
    )


def test_order_admin_retry_failed_delivery_action_creates_new_current_shipment(order_admin):
    user = User.objects.create_user(email="order-admin-action-retry@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    original_shipment = ShipmentService.create_for_paid_order(order=order)
    OrderFulfillmentService.move_current_shipment_to_in_transit(order=order)
    OrderFulfillmentService.move_current_shipment_to_failed_delivery(order=order)
    request = _request_with_messages()

    order_admin.retry_failed_delivery(request, Order.objects.filter(pk=order.pk))

    order.refresh_from_db()
    original_shipment.refresh_from_db()
    current_shipment = order.get_current_shipment()
    stored = list(messages.get_messages(request))

    assert Shipment.objects.filter(order=order).count() == 2
    assert original_shipment.status == ShipmentStatus.FAILED_DELIVERY
    assert current_shipment is not None
    assert current_shipment.pk != original_shipment.pk
    assert current_shipment.status == ShipmentStatus.LABEL_CREATED
    assert order.status == Order.Status.PAID
    assert len(stored) == 1
    assert str(stored[0]) == "Retry failed delivery: 1 orders updated."


def test_order_admin_bulk_action_delegates_to_fulfillment_service(monkeypatch, order_admin):
    user = User.objects.create_user(email="order-admin-action-service@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    request = _request_with_messages()
    captured_ids = []

    def fake_bulk_move_current_shipment_to_delivered(*, orders):
        captured_ids.extend(item.pk for item in orders)
        return BulkOrderFulfillmentResult(updated_count=1)

    monkeypatch.setattr(
        OrderFulfillmentService,
        "bulk_move_current_shipment_to_delivered",
        fake_bulk_move_current_shipment_to_delivered,
    )

    order_admin.move_current_shipment_to_delivered(request, Order.objects.filter(pk=order.pk))

    stored = list(messages.get_messages(request))

    assert captured_ids == [order.pk]
    assert len(stored) == 1
    assert str(stored[0]) == "Move current shipment to Delivered: 1 orders updated."