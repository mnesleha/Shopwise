import threading
from dataclasses import dataclass

import pytest
from django.db import close_old_connections, transaction

from api.exceptions.orders import OutOfStockException
from orders.models import Order, InventoryReservation
from products.models import Product
from tests.conftest import create_valid_order

from orders.services.inventory_reservation_service import reserve_for_checkout


@dataclass
class WorkerResult:
    ok: bool
    exc: Exception | None = None


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_mysql_two_concurrent_reserves_compete_for_last_stock():
    """
    Two concurrent reservations for the last unit of stock:
    - exactly one succeeds
    - the other fails with OutOfStockError
    """
    product = Product.objects.create(
        name="Race Product",
        price="10.00",
        stock_quantity=1,
        is_active=True,
    )

    order1 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g1@example.com")
    order2 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g2@example.com")

    barrier = threading.Barrier(2)
    results: list[WorkerResult] = []
    lock = threading.Lock()

    def worker(order: Order):
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait()
                reserve_for_checkout(
                    order=order,
                    items=[{"product_id": product.id, "quantity": 1}],
                )
            with lock:
                results.append(WorkerResult(ok=True))
        except Exception as e:
            with lock:
                results.append(WorkerResult(ok=False, exc=e))

    t1 = threading.Thread(target=worker, args=(order1,))
    t2 = threading.Thread(target=worker, args=(order2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    oks = [r for r in results if r.ok]
    fails = [r for r in results if not r.ok]

    assert len(oks) == 1
    assert len(fails) == 1
    assert isinstance(fails[0].exc, OutOfStockException)

    # Optional extra assertion: only one ACTIVE reservation exists for the product across both orders
    assert InventoryReservation.objects.filter(
        product=product, status=InventoryReservation.Status.ACTIVE).count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_mysql_lock_ordering_avoids_deadlocks_for_multi_product_reserve():
    """
    Two concurrent reserves with reversed item order must not deadlock.
    Service must lock products in deterministic order (sorted product_ids).
    """
    a = Product.objects.create(
        name="A", price="10.00", stock_quantity=1, is_active=True)
    b = Product.objects.create(
        name="B", price="10.00", stock_quantity=1, is_active=True)

    order1 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g1@example.com")
    order2 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="g2@example.com")

    barrier = threading.Barrier(2)
    results: list[WorkerResult] = []
    lock = threading.Lock()

    items1 = [{"product_id": a.id, "quantity": 1},
              {"product_id": b.id, "quantity": 1}]
    items2 = [{"product_id": b.id, "quantity": 1}, {
        "product_id": a.id, "quantity": 1}]  # reversed

    def worker(order: Order, items):
        close_old_connections()
        try:
            with transaction.atomic():
                barrier.wait()
                reserve_for_checkout(order=order, items=items)
            with lock:
                results.append(WorkerResult(ok=True))
        except Exception as e:
            with lock:
                results.append(WorkerResult(ok=False, exc=e))

    t1 = threading.Thread(target=worker, args=(order1, items1))
    t2 = threading.Thread(target=worker, args=(order2, items2))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # We don't assert both must succeed (stock may be exhausted depending on timing),
    # but we do assert "no deadlock" and the outcomes are well-formed.
    assert len(results) == 2
    assert any(r.ok for r in results)

    # If one fails, it should be due to stock, not a DB deadlock.
    for r in results:
        if not r.ok:
            assert isinstance(r.exc, OutOfStockException)
