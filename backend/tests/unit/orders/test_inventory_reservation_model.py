from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from conftest import create_valid_order
from orders.models import Order, InventoryReservation
from products.models import Product


def _create_product(stock=10):
    return Product.objects.create(
        name="Reservation Product",
        price="10.00",
        stock_quantity=stock,
        is_active=True,
    )


@pytest.mark.django_db
def test_inventory_reservation_can_be_created_minimal():
    """
    Minimal happy path:
    - order + product + quantity + expires_at
    - default status must be ACTIVE
    """
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    product = _create_product(stock=10)
    expires_at = timezone.now() + timedelta(minutes=15)

    r = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=2,
        expires_at=expires_at,
    )

    assert r.pk is not None
    assert r.status == InventoryReservation.Status.ACTIVE
    assert r.expires_at == expires_at
    assert r.release_reason is None


@pytest.mark.django_db
def test_inventory_reservation_quantity_must_be_positive():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    product = _create_product(stock=10)
    expires_at = timezone.now() + timedelta(minutes=15)

    r = InventoryReservation(
        order=order,
        product=product,
        quantity=0,
        expires_at=expires_at,
    )

    with pytest.raises(ValidationError) as e:
        r.full_clean()

    assert "quantity" in e.value.message_dict


@pytest.mark.django_db
def test_inventory_reservation_expires_at_is_required():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    product = _create_product(stock=10)

    r = InventoryReservation(
        order=order,
        product=product,
        quantity=1,
        expires_at=None,
    )

    with pytest.raises(ValidationError) as e:
        r.full_clean()

    assert "expires_at" in e.value.message_dict


@pytest.mark.django_db
def test_inventory_reservation_is_unique_per_order_and_product():
    """
    Exactly one reservation row per (order, product).
    State changes happen via status updates on the same row.
    """
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    product = _create_product(stock=10)
    expires_at = timezone.now() + timedelta(minutes=15)

    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=expires_at,
    )

    with pytest.raises(IntegrityError):
        InventoryReservation.objects.create(
            order=order,
            product=product,
            quantity=1,
            expires_at=expires_at,
        )


@pytest.mark.django_db
def test_inventory_reservation_expired_property():
    """
    Model helper:
    - is_expired reflects expires_at < now AND status ACTIVE
    """
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    product = _create_product(stock=10)

    r = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    assert r.is_expired is True
    assert r.is_active is True


@pytest.mark.django_db
def test_inventory_reservation_not_active_when_committed():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    product = _create_product(stock=10)

    r = InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        expires_at=timezone.now() + timedelta(minutes=15),
        status=InventoryReservation.Status.COMMITTED,
    )

    assert r.is_active is False
    assert r.is_expired is False
