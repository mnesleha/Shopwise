from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from orders.models import Order, InventoryReservation
from products.models import Product
from tests.conftest import create_valid_order

from orders.services.inventory_reservation_service import reserve_for_checkout


def _create_product(stock=10):
    return Product.objects.create(
        name="TTL Product",
        price="10.00",
        stock_quantity=stock,
        is_active=True,
    )


@pytest.mark.django_db
@override_settings(RESERVATION_TTL_GUEST_SECONDS=60, RESERVATION_TTL_AUTH_SECONDS=7200)
def test_reserve_for_checkout_uses_guest_ttl_when_order_has_no_user(django_user_model):
    """
    Guest order (order.user is NULL) must use guest TTL setting.
    """
    product = _create_product(stock=10)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    before = timezone.now()
    reserve_for_checkout(
        order=order,
        items=[{"product_id": product.id, "quantity": 1}],
    )
    after = timezone.now()

    r = InventoryReservation.objects.get(order=order, product=product)
    assert r.status == InventoryReservation.Status.ACTIVE

    # expires_at should be roughly now + 60s (allow small time drift)
    assert before + \
        timedelta(seconds=55) <= r.expires_at <= after + timedelta(seconds=65)


@pytest.mark.django_db
@override_settings(RESERVATION_TTL_GUEST_SECONDS=60, RESERVATION_TTL_AUTH_SECONDS=7200)
def test_reserve_for_checkout_uses_auth_ttl_when_order_has_user(django_user_model):
    """
    Authenticated order (order.user is set) must use auth TTL setting.
    """
    product = _create_product(stock=10)
    user = django_user_model.objects.create_user(
        email="u@example.com", password="pass12345")

    order = create_valid_order(
        user=user, status=Order.Status.CREATED, customer_email="u@example.com")

    before = timezone.now()
    reserve_for_checkout(
        order=order,
        items=[{"product_id": product.id, "quantity": 1}],
    )
    after = timezone.now()

    r = InventoryReservation.objects.get(order=order, product=product)
    assert r.status == InventoryReservation.Status.ACTIVE

    # expires_at should be roughly now + 7200s
    assert before + \
        timedelta(seconds=7190) <= r.expires_at <= after + \
        timedelta(seconds=7210)
