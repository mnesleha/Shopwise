import pytest
from datetime import timedelta
from django.utils import timezone

from orders.models import Order, InventoryReservation
from orders.services.inventory_reservation_service import count_overdue_reservations
from products.models import Product
from tests.conftest import create_valid_order


@pytest.mark.django_db
def test_count_overdue_reservations_returns_zero_when_none_overdue():
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    assert count_overdue_reservations(now=timezone.now()) == 0


@pytest.mark.django_db
def test_count_overdue_reservations_counts_only_active_and_created():
    """
    count_overdue_reservations() should count only reservations that are:
    - status == ACTIVE
    - expires_at < now
    - order.status == CREATED

    It must ignore:
    - non-CREATED orders
    - non-ACTIVE reservation statuses
    - reservations that are not overdue
    """
    now = timezone.now()

    # Create distinct products to avoid unique constraint on (order, product)
    product_counted = Product.objects.create(
        name="P_COUNTED", price=10, stock_quantity=10, is_active=True)
    product_paid_order = Product.objects.create(
        name="P_PAID_ORDER", price=10, stock_quantity=10, is_active=True)
    product_not_active = Product.objects.create(
        name="P_NOT_ACTIVE", price=10, stock_quantity=10, is_active=True)
    product_not_overdue = Product.objects.create(
        name="P_NOT_OVERDUE", price=10, stock_quantity=10, is_active=True)

    order_created = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="created@example.com"
    )
    order_paid = create_valid_order(
        user=None, status=Order.Status.PAID, customer_email="paid@example.com"
    )

    # should count: ACTIVE + overdue + order CREATED
    InventoryReservation.objects.create(
        order=order_created,
        product=product_counted,
        quantity=1,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=now - timedelta(seconds=1),
    )

    # should NOT count: order not CREATED (PAID)
    InventoryReservation.objects.create(
        order=order_paid,
        product=product_paid_order,
        quantity=1,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=now - timedelta(seconds=1),
    )

    # should NOT count: not ACTIVE (RELEASED), even if overdue and order CREATED
    InventoryReservation.objects.create(
        order=order_created,
        product=product_not_active,
        quantity=1,
        status=InventoryReservation.Status.RELEASED,
        expires_at=now - timedelta(seconds=1),
    )

    # should NOT count: not overdue, even if ACTIVE and order CREATED
    InventoryReservation.objects.create(
        order=order_created,
        product=product_not_overdue,
        quantity=1,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=now + timedelta(minutes=10),
    )

    assert count_overdue_reservations(now=now) == 1


@pytest.mark.django_db
def test_count_overdue_reservations_counts_multiple_overdue_reservations_across_orders():
    now = timezone.now()
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    o1 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="a@example.com")
    o2 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="b@example.com")

    InventoryReservation.objects.create(
        order=o1,
        product=product,
        quantity=1,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=now - timedelta(minutes=1),
    )
    InventoryReservation.objects.create(
        order=o2,
        product=product,
        quantity=2,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=now - timedelta(minutes=1),
    )

    assert count_overdue_reservations(now=now) == 2
