from datetime import timedelta

import pytest
from django.utils import timezone

from api.exceptions.orders import OutOfStockException
from orders.models import Order, InventoryReservation
from products.models import Product
from tests.conftest import create_valid_order

from orders.services.inventory_reservation_service import (
    reserve_for_checkout,
    commit_reservations_for_paid,
    release_reservations,
    expire_overdue_reservations,
)

from auditlog.models import AuditEvent
from auditlog.actions import AuditActions


def _create_product(stock=10):
    return Product.objects.create(
        name="Service Product",
        price="10.00",
        stock_quantity=stock,
        is_active=True,
    )


@pytest.mark.django_db
def test_commit_reservations_decrements_physical_stock_and_marks_committed(django_user_model):
    product = _create_product(stock=10)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 2}], ttl_minutes=15)

    commit_reservations_for_paid(order=order)

    product.refresh_from_db()
    order.refresh_from_db()

    r = InventoryReservation.objects.get(order=order, product=product)

    assert order.status == Order.Status.PAID
    assert r.status == InventoryReservation.Status.COMMITTED
    assert r.committed_at is not None
    assert product.stock_quantity == 8


@pytest.mark.django_db
def test_commit_is_idempotent_single_thread():
    product = _create_product(stock=10)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 2}], ttl_minutes=15)

    commit_reservations_for_paid(order=order)
    commit_reservations_for_paid(order=order)

    product.refresh_from_db()
    order.refresh_from_db()
    r = InventoryReservation.objects.get(order=order, product=product)

    assert order.status == Order.Status.PAID
    assert r.status == InventoryReservation.Status.COMMITTED
    assert product.stock_quantity == 8  # decremented only once


@pytest.mark.django_db
def test_release_reservations_cancels_created_order_and_releases_active_reservations():
    product = _create_product(stock=10)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 2}], ttl_minutes=15)

    release_reservations(
        order=order,
        reason=InventoryReservation.ReleaseReason.CUSTOMER_REQUEST,
        cancelled_by=Order.CancelledBy.CUSTOMER,
        cancel_reason=Order.CancelReason.CUSTOMER_REQUEST,
    )

    product.refresh_from_db()
    order.refresh_from_db()
    r = InventoryReservation.objects.get(order=order, product=product)

    assert order.status == Order.Status.CANCELLED
    assert order.cancel_reason == Order.CancelReason.CUSTOMER_REQUEST
    assert order.cancelled_by == Order.CancelledBy.CUSTOMER
    assert order.cancelled_at is not None

    assert r.status == InventoryReservation.Status.RELEASED
    assert r.release_reason == InventoryReservation.ReleaseReason.CUSTOMER_REQUEST
    assert r.released_at is not None

    # Stock was NOT decremented on reserve, so release does not restock.
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_release_is_idempotent():
    product = _create_product(stock=10)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 1}], ttl_minutes=15)

    release_reservations(
        order=order,
        reason=InventoryReservation.ReleaseReason.CUSTOMER_REQUEST,
        cancelled_by=Order.CancelledBy.CUSTOMER,
        cancel_reason=Order.CancelReason.CUSTOMER_REQUEST,
    )
    # second call should not blow up and should not change stock
    release_reservations(
        order=order,
        reason=InventoryReservation.ReleaseReason.CUSTOMER_REQUEST,
        cancelled_by=Order.CancelledBy.CUSTOMER,
        cancel_reason=Order.CancelReason.CUSTOMER_REQUEST,
    )

    product.refresh_from_db()
    order.refresh_from_db()
    r = InventoryReservation.objects.get(order=order, product=product)

    assert order.status == Order.Status.CANCELLED
    assert r.status == InventoryReservation.Status.RELEASED
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_expire_overdue_reservations_expires_active_and_cancels_created_order():
    product = _create_product(stock=10)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 1}], ttl_minutes=15)

    # Force overdue
    InventoryReservation.objects.filter(order=order, product=product).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    affected = expire_overdue_reservations(now=timezone.now())

    order.refresh_from_db()
    r = InventoryReservation.objects.get(order=order, product=product)

    assert affected >= 1
    assert order.status == Order.Status.CANCELLED
    assert order.cancel_reason == Order.CancelReason.PAYMENT_EXPIRED

    # Depending on your model: EXPIRED terminal OR RELEASED with PAYMENT_EXPIRED.
    assert r.status in (InventoryReservation.Status.EXPIRED,
                        InventoryReservation.Status.RELEASED)
    if r.status == InventoryReservation.Status.RELEASED:
        assert r.release_reason == InventoryReservation.ReleaseReason.PAYMENT_EXPIRED
    assert r.released_at is not None or r.status == InventoryReservation.Status.EXPIRED

    # Audit: system TTL expiry should emit inventory + order cancellation events
    inv_ev = AuditEvent.objects.filter(
        entity_type="inventory_reservation_batch",
        entity_id=str(order.id),
        action=AuditActions.INVENTORY_RESERVATIONS_EXPIRED,
    ).order_by("-created_at", "-id").first()
    assert inv_ev is not None
    assert inv_ev.actor_type == AuditEvent.ActorType.SYSTEM
    assert inv_ev.metadata.get("affected_reservations", 0) >= 1

    order_ev = AuditEvent.objects.filter(
        entity_type="order",
        entity_id=str(order.id),
        action=AuditActions.ORDER_CANCELLED,
    ).order_by("-created_at", "-id").first()
    assert order_ev is not None
    assert order_ev.actor_type == AuditEvent.ActorType.SYSTEM
    assert order_ev.metadata.get(
        "cancel_reason") == Order.CancelReason.PAYMENT_EXPIRED


@pytest.mark.django_db
def test_commit_fails_if_availability_was_over_reserved_via_active_sum_semantics():
    """
    Guardrail test for ADR-025 semantics:
    availability for reserve is physical_stock - sum(ACTIVE reservations).
    We simulate "stock=1" and an existing ACTIVE reservation of qty=1 on another order, then reserve must fail.
    """
    product = _create_product(stock=1)

    order1 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g1@example.com")
    order2 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g2@example.com")

    reserve_for_checkout(order=order1, items=[
                         {"product_id": product.id, "quantity": 1}], ttl_minutes=15)

    with pytest.raises(OutOfStockException):
        reserve_for_checkout(order=order2, items=[
                             {"product_id": product.id, "quantity": 1}], ttl_minutes=15)
