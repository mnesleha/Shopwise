import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from orders.models import Order
from payments.models import Payment
from shipping.models import Shipment
from shipping.services.shipment import InvalidShipmentSnapshot, ShipmentService
from shipping.statuses import ShipmentStatus
from tests.conftest import create_valid_order

User = get_user_model()


@pytest.mark.django_db
def test_create_for_paid_order_persists_provider_result_and_stored_label(tmp_path):
    user = User.objects.create_user(email="shipment-service@example.com", password="pass")
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        order = create_valid_order(
            user=user,
            status=Order.Status.PAID,
            shipping_provider_code="MOCK",
            shipping_service_code="express",
        )

        shipment = ShipmentService.create_for_paid_order(order=order)

        assert shipment.order == order
        assert shipment.provider_code == "MOCK"
        assert shipment.service_code == "express"
        assert shipment.carrier_name_snapshot == "Mock Carrier"
        assert shipment.service_name_snapshot == "Express"
        assert shipment.status == ShipmentStatus.LABEL_CREATED
        assert shipment.tracking_number == f"MOCK-{order.pk}-EXPRESS-A1"
        assert shipment.carrier_reference == f"REF-MOCK-{order.pk}-EXPRESS-A1"
        assert shipment.label_file.name.endswith(".svg")
        assert shipment.label_url == shipment.get_label_url()
        assert shipment.label_url.startswith("/media/shipping/labels/")
        assert shipment.receiver_snapshot["city"] == order.shipping_city
        assert shipment.meta == {"mock": True}

        label_path = shipment.label_file.path
        with open(label_path, "r", encoding="utf-8") as stored_label:
            content = stored_label.read()

        assert "Mock Carrier - Express" in content
        assert f"MOCK-{order.pk}-EXPRESS-A1" in content
        assert f"Order #{order.pk}" in content


@pytest.mark.django_db
def test_create_for_paid_order_is_idempotent_for_existing_shipment():
    user = User.objects.create_user(email="shipment-idem@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)

    first = ShipmentService.create_for_paid_order(order=order)
    second = ShipmentService.create_for_paid_order(order=order)

    assert first.pk == second.pk
    assert Shipment.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_create_for_paid_order_rejects_non_paid_order():
    user = User.objects.create_user(email="shipment-nonpaid@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.CREATED)

    with pytest.raises(ValueError, match="fulfillment-eligible"):
        ShipmentService.create_for_order(order=order)


@pytest.mark.django_db
def test_create_for_order_allows_created_cod_order_with_pending_payment():
    user = User.objects.create_user(email="shipment-cod@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.CREATED)
    Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        payment_method=Payment.PaymentMethod.COD,
        provider=Payment.Provider.DEV_FAKE,
    )

    shipment = ShipmentService.create_for_order(order=order)

    order.refresh_from_db()

    assert shipment.status == ShipmentStatus.LABEL_CREATED
    assert order.status == Order.Status.CREATED


@pytest.mark.django_db
def test_create_for_order_rejects_created_card_order_before_payment():
    user = User.objects.create_user(email="shipment-card@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.CREATED)
    Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        payment_method=Payment.PaymentMethod.CARD,
        provider=Payment.Provider.ACQUIREMOCK,
    )

    with pytest.raises(ValueError, match="fulfillment-eligible"):
        ShipmentService.create_for_order(order=order)


@pytest.mark.django_db
def test_create_for_order_rejects_payment_failed_cod_order():
    user = User.objects.create_user(email="shipment-payment-failed@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAYMENT_FAILED)
    Payment.objects.create(
        order=order,
        status=Payment.Status.FAILED,
        payment_method=Payment.PaymentMethod.COD,
        provider=Payment.Provider.DEV_FAKE,
    )

    with pytest.raises(ValueError, match="fulfillment-eligible"):
        ShipmentService.create_for_order(order=order)


@pytest.mark.django_db
def test_create_for_order_rejects_cancelled_cod_order():
    user = User.objects.create_user(email="shipment-cancelled@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.CANCELLED)
    Payment.objects.create(
        order=order,
        status=Payment.Status.PENDING,
        payment_method=Payment.PaymentMethod.COD,
        provider=Payment.Provider.DEV_FAKE,
    )

    with pytest.raises(ValueError, match="fulfillment-eligible"):
        ShipmentService.create_for_order(order=order)


@pytest.mark.django_db
def test_create_for_paid_order_rejects_missing_shipping_snapshot(monkeypatch):
    user = User.objects.create_user(email="shipment-missing-snapshot@example.com", password="pass")
    order = create_valid_order(user=user, status=Order.Status.PAID)
    order.shipping_provider_code = ""
    order.shipping_service_code = ""
    order.save(update_fields=["shipping_provider_code", "shipping_service_code"])

    def fail_if_resolver_called(*args, **kwargs):
        raise AssertionError("resolver should not be called for invalid shipping snapshot")

    monkeypatch.setattr("shipping.services.shipment.resolve_provider", fail_if_resolver_called)

    with pytest.raises(InvalidShipmentSnapshot, match="shipping_provider_code, shipping_service_code"):
        ShipmentService.create_for_order(order=order)