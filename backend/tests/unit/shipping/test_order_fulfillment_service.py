import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from orders.models import Order
from payments.models import Payment
from shipping.models import Shipment, ShipmentEvent
from shipping.services.fulfillment import OrderFulfillmentService
from shipping.services.shipment import ShipmentService
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order

User = get_user_model()


@pytest.mark.django_db
def test_create_missing_shipment_for_paid_order_without_shipment_creates_new_shipment():
    user = User.objects.create_user(email="fulfillment-create@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)

    outcome = OrderFulfillmentService.create_missing_shipment_for_order(order=order)

    order.refresh_from_db()
    shipment = order.get_current_shipment()

    assert outcome == "updated"
    assert shipment is not None
    assert shipment.status == ShipmentStatus.LABEL_CREATED
    assert shipment.provider_code == order.shipping_provider_code


@pytest.mark.django_db
def test_bulk_create_missing_shipments_skips_invalid_orders():
    user = User.objects.create_user(email="fulfillment-create-invalid@example.com", password="pass")
    valid_order = create_valid_order(user=user, status=Order.Status.PAID)
    non_paid_order = create_valid_order(user=user, status=Order.Status.CREATED)
    existing_shipment_order = create_valid_order(user=user, status=Order.Status.PAID)
    ShipmentService.create_for_paid_order(order=existing_shipment_order)

    result = OrderFulfillmentService.bulk_create_missing_shipments(
        orders=Order.objects.filter(
            pk__in=[valid_order.pk, non_paid_order.pk, existing_shipment_order.pk],
        ).order_by("pk"),
    )

    valid_order.refresh_from_db()
    non_paid_order.refresh_from_db()
    existing_shipment_order.refresh_from_db()

    assert result.updated_count == 1
    assert result.skipped_counts["invalid_order_status"] == 1
    assert result.skipped_counts["shipment_already_exists"] == 1
    assert Shipment.objects.filter(order=valid_order).count() == 1
    assert Shipment.objects.filter(order=non_paid_order).count() == 0
    assert Shipment.objects.filter(order=existing_shipment_order).count() == 1


@pytest.mark.django_db
def test_create_missing_shipment_for_created_cod_order_creates_shipment_without_marking_paid():
    user = User.objects.create_user(email="fulfillment-create-cod@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.CREATED)
    Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        payment_method=Payment.PaymentMethod.COD,
        provider=Payment.Provider.DEV_FAKE,
    )

    outcome = OrderFulfillmentService.create_missing_shipment_for_order(order=order)

    order.refresh_from_db()
    shipment = order.get_current_shipment()

    assert outcome == "updated"
    assert shipment is not None
    assert shipment.status == ShipmentStatus.LABEL_CREATED
    assert order.status == Order.Status.CREATED


@pytest.mark.django_db
def test_move_current_shipment_to_in_transit_only_works_from_label_created():
    user = User.objects.create_user(email="fulfillment-transit@example.com", password="pass")
    valid_order = create_valid_order(user=user, status=Order.Status.PAID)
    valid_shipment = ShipmentService.create_for_paid_order(order=valid_order)
    invalid_order = create_valid_order(user=user, status=Order.Status.SHIPPED)
    invalid_shipment = Shipment.objects.create(
        order=invalid_order,
        provider_code="MOCK",
        service_code="standard",
        carrier_name_snapshot="Mock Carrier",
        service_name_snapshot="Standard",
        tracking_number="MOCK-INVALID-TRANSIT",
        status=ShipmentStatus.IN_TRANSIT,
    )

    valid_outcome = OrderFulfillmentService.move_current_shipment_to_in_transit(order=valid_order)
    invalid_outcome = OrderFulfillmentService.move_current_shipment_to_in_transit(order=invalid_order)

    valid_shipment.refresh_from_db()
    valid_order.refresh_from_db()
    invalid_shipment.refresh_from_db()
    invalid_order.refresh_from_db()

    assert valid_outcome == "updated"
    assert valid_shipment.status == ShipmentStatus.IN_TRANSIT
    assert valid_order.status == Order.Status.SHIPPED
    assert ShipmentEvent.objects.filter(shipment=valid_shipment, normalized_status=ShipmentStatus.IN_TRANSIT).count() == 1
    assert invalid_outcome == "invalid_shipment_status"
    assert invalid_shipment.status == ShipmentStatus.IN_TRANSIT
    assert invalid_order.status == Order.Status.SHIPPED


@pytest.mark.django_db
def test_move_current_shipment_to_delivered_only_works_from_in_transit():
    user = User.objects.create_user(email="fulfillment-delivered@example.com", password="pass")
    valid_order = create_valid_order(user=user, status=Order.Status.PAID)
    valid_shipment = ShipmentService.create_for_paid_order(order=valid_order)
    OrderFulfillmentService.move_current_shipment_to_in_transit(order=valid_order)
    invalid_order = create_valid_order(user=user, status=Order.Status.PAID)
    invalid_shipment = ShipmentService.create_for_paid_order(order=invalid_order)

    valid_outcome = OrderFulfillmentService.move_current_shipment_to_delivered(order=valid_order)
    invalid_outcome = OrderFulfillmentService.move_current_shipment_to_delivered(order=invalid_order)

    valid_shipment.refresh_from_db()
    valid_order.refresh_from_db()
    invalid_shipment.refresh_from_db()
    invalid_order.refresh_from_db()

    assert valid_outcome == "updated"
    assert valid_shipment.status == ShipmentStatus.DELIVERED
    assert valid_order.status == Order.Status.DELIVERED
    assert ShipmentEvent.objects.filter(shipment=valid_shipment, normalized_status=ShipmentStatus.DELIVERED).count() == 1
    assert invalid_outcome == "invalid_shipment_status"
    assert invalid_shipment.status == ShipmentStatus.LABEL_CREATED
    assert invalid_order.status == Order.Status.PAID


@pytest.mark.django_db
def test_move_current_shipment_to_failed_delivery_only_works_from_in_transit():
    user = User.objects.create_user(email="fulfillment-failed@example.com", password="pass")
    valid_order = create_valid_order(user=user, status=Order.Status.PAID)
    valid_shipment = ShipmentService.create_for_paid_order(order=valid_order)
    OrderFulfillmentService.move_current_shipment_to_in_transit(order=valid_order)
    invalid_order = create_valid_order(user=user, status=Order.Status.PAID)
    invalid_shipment = ShipmentService.create_for_paid_order(order=invalid_order)

    valid_outcome = OrderFulfillmentService.move_current_shipment_to_failed_delivery(order=valid_order)
    invalid_outcome = OrderFulfillmentService.move_current_shipment_to_failed_delivery(order=invalid_order)

    valid_shipment.refresh_from_db()
    valid_order.refresh_from_db()
    invalid_shipment.refresh_from_db()
    invalid_order.refresh_from_db()

    assert valid_outcome == "updated"
    assert valid_shipment.status == ShipmentStatus.FAILED_DELIVERY
    assert valid_order.status == Order.Status.DELIVERY_FAILED
    assert ShipmentEvent.objects.filter(shipment=valid_shipment, normalized_status=ShipmentStatus.FAILED_DELIVERY).count() == 1
    assert invalid_outcome == "invalid_shipment_status"
    assert invalid_shipment.status == ShipmentStatus.LABEL_CREATED
    assert invalid_order.status == Order.Status.PAID


@pytest.mark.django_db
def test_retry_failed_delivery_creates_new_shipment_and_preserves_old_failed_shipment():
    user = User.objects.create_user(email="fulfillment-retry@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    original_shipment = ShipmentService.create_for_paid_order(order=order)
    OrderFulfillmentService.move_current_shipment_to_in_transit(order=order)
    OrderFulfillmentService.move_current_shipment_to_failed_delivery(order=order)

    outcome = OrderFulfillmentService.retry_failed_delivery(order=order)

    order.refresh_from_db()
    original_shipment.refresh_from_db()
    shipments = list(order.shipments.all())
    current_shipment = order.get_current_shipment()

    assert outcome == "updated"
    assert len(shipments) == 2
    assert original_shipment.status == ShipmentStatus.FAILED_DELIVERY
    assert current_shipment is not None
    assert current_shipment.pk != original_shipment.pk
    assert current_shipment.status == ShipmentStatus.LABEL_CREATED
    assert current_shipment.provider_code == original_shipment.provider_code
    assert current_shipment.service_code == original_shipment.service_code
    assert current_shipment.tracking_number != original_shipment.tracking_number
    assert current_shipment.carrier_reference != original_shipment.carrier_reference
    assert order.status == Order.Status.PAID


@pytest.mark.django_db
def test_retry_failed_delivery_regenerates_mock_label_identity(tmp_path):
    user = User.objects.create_user(email="fulfillment-retry-label@example.com", password="pass")
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        order = create_valid_order(user=user, status=Order.Status.PAID)
        original_shipment = ShipmentService.create_for_paid_order(order=order)
        original_label_name = original_shipment.label_file.name
        original_label_url = original_shipment.label_url
        OrderFulfillmentService.move_current_shipment_to_in_transit(order=order)
        OrderFulfillmentService.move_current_shipment_to_failed_delivery(order=order)

        outcome = OrderFulfillmentService.retry_failed_delivery(order=order)

        original_shipment.refresh_from_db()
        current_shipment = order.get_current_shipment()

        assert outcome == "updated"
        assert current_shipment is not None
        assert current_shipment.pk != original_shipment.pk
        assert current_shipment.label_file.name != original_label_name
        assert current_shipment.label_url != original_label_url
        assert current_shipment.label_file.name.endswith(".svg")


@pytest.mark.django_db
def test_retry_failed_delivery_requires_failed_current_shipment():
    user = User.objects.create_user(email="fulfillment-retry-invalid@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    ShipmentService.create_for_paid_order(order=order)

    outcome = OrderFulfillmentService.retry_failed_delivery(order=order)

    order.refresh_from_db()

    assert outcome == "invalid_shipment_status"
    assert Shipment.objects.filter(order=order).count() == 1
    assert order.status == Order.Status.PAID