import threading
from dataclasses import dataclass
from datetime import timedelta

import pytest
from django.db import close_old_connections, transaction
from django.utils import timezone

from orders.models import Order, InventoryReservation
from products.models import Product
from tests.conftest import create_valid_order

from orders.services.inventory_reservation_service import (
    reserve_for_checkout,
    commit_reservations_for_paid,
    release_reservations,
    expire_overdue_reservations,
)


@dataclass
class WorkerResult:
    ok: bool
    exc: Exception | None = None


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_mysql_concurrent_commit_is_idempotent_no_double_decrement():
    """
    Two concurrent commits on the SAME order must not double-decrement physical stock.
    """
    product = Product.objects.create(
        name="Commit Race", price="10.00", stock_quantity=10, is_active=True)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 2}], ttl_minutes=15)

    barrier = threading.Barrier(2)
    results: list[WorkerResult] = []
    lock = threading.Lock()

    def worker():
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait()
                commit_reservations_for_paid(order=order)
            with lock:
                results.append(WorkerResult(ok=True))
        except Exception as e:
            with lock:
                results.append(WorkerResult(ok=False, exc=e))

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    assert all(r.ok for r in results)

    product.refresh_from_db()
    order.refresh_from_db()
    r = InventoryReservation.objects.get(order=order, product=product)

    assert order.status == Order.Status.PAID
    assert r.status == InventoryReservation.Status.COMMITTED
    assert product.stock_quantity == 8  # decremented exactly once


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_mysql_commit_vs_expire_race_final_state_is_consistent():
    """
    Commit (payment success) racing with expire job (TTL) must end in a consistent state.
    Acceptable outcomes:
    A) commit wins -> PAID + COMMITTED + stock decremented
    B) expire wins -> CANCELLED(PAYMENT_EXPIRED) + EXPIRED/RELEASED + stock NOT decremented
    Must NEVER happen:
    - double decrement
    - PAID with non-COMMITTED reservation
    - CANCELLED with stock decremented for this order's qty
    """
    product = Product.objects.create(
        name="Commit/Expire Race", price="10.00", stock_quantity=10, is_active=True)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 2}], ttl_minutes=15)

    # Force overdue
    InventoryReservation.objects.filter(order=order, product=product).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )

    barrier = threading.Barrier(2)
    results: list[WorkerResult] = []
    lock = threading.Lock()

    def worker_commit():
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait()
                commit_reservations_for_paid(order=order)
            with lock:
                results.append(WorkerResult(ok=True))
        except Exception as e:
            with lock:
                results.append(WorkerResult(ok=False, exc=e))

    def worker_expire():
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait()
                expire_overdue_reservations(now=timezone.now())
            with lock:
                results.append(WorkerResult(ok=True))
        except Exception as e:
            with lock:
                results.append(WorkerResult(ok=False, exc=e))

    t1 = threading.Thread(target=worker_commit)
    t2 = threading.Thread(target=worker_expire)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2  # either/both may "ok" depending on idempotence

    product.refresh_from_db()
    order.refresh_from_db()
    r = InventoryReservation.objects.get(order=order, product=product)

    if order.status == Order.Status.PAID:
        assert r.status == InventoryReservation.Status.COMMITTED
        assert product.stock_quantity == 8
    elif order.status == Order.Status.CANCELLED:
        assert order.cancel_reason == Order.CancelReason.PAYMENT_EXPIRED
        assert r.status in (InventoryReservation.Status.EXPIRED,
                            InventoryReservation.Status.RELEASED)
        assert product.stock_quantity == 10
    else:
        raise AssertionError(f"Unexpected final order status: {order.status}")


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_mysql_commit_vs_release_race_is_consistent():
    """
    Commit racing with release must end consistently.
    Acceptable:
    - commit wins -> PAID + COMMITTED + stock decremented
    - release wins -> CANCELLED + RELEASED + stock unchanged
    """
    product = Product.objects.create(
        name="Commit/Release Race", price="10.00", stock_quantity=10, is_active=True)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g@example.com")

    reserve_for_checkout(order=order, items=[
                         {"product_id": product.id, "quantity": 2}], ttl_minutes=15)

    barrier = threading.Barrier(2)
    results: list[WorkerResult] = []
    lock = threading.Lock()

    def worker_commit():
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait()
                commit_reservations_for_paid(order=order)
            with lock:
                results.append(WorkerResult(ok=True))
        except Exception as e:
            with lock:
                results.append(WorkerResult(ok=False, exc=e))

    def worker_release():
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait()
                release_reservations(
                    order=order,
                    reason=InventoryReservation.ReleaseReason.CUSTOMER_REQUEST,
                    cancelled_by=Order.CancelledBy.CUSTOMER,
                    cancel_reason=Order.CancelReason.CUSTOMER_REQUEST,
                )
            with lock:
                results.append(WorkerResult(ok=True))
        except Exception as e:
            with lock:
                results.append(WorkerResult(ok=False, exc=e))

    t1 = threading.Thread(target=worker_commit)
    t2 = threading.Thread(target=worker_release)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    product.refresh_from_db()
    order.refresh_from_db()
    r = InventoryReservation.objects.get(order=order, product=product)

    if order.status == Order.Status.PAID:
        assert r.status == InventoryReservation.Status.COMMITTED
        assert product.stock_quantity == 8
    elif order.status == Order.Status.CANCELLED:
        assert r.status == InventoryReservation.Status.RELEASED
        assert product.stock_quantity == 10
    else:
        raise AssertionError(f"Unexpected final order status: {order.status}")
