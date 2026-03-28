import pytest
from django.utils import timezone

from orders.models import Order, InventoryReservation
from orders.services.inventory_reservation_service import reserve_for_checkout
from products.models import Product
from payments.models import Payment
from tests.conftest import checkout_payload, create_order_via_checkout, create_valid_order


# ---------------------------------------------------------------------------
# Inline helper: set up an order in CREATED state with an ACTIVE reservation
# without triggering checkout's auto-payment.  Use this instead of
# create_order_via_checkout() when the test needs to exercise the payment
# endpoint directly (e.g. failure + retry scenarios).
# ---------------------------------------------------------------------------

def _create_order_with_reservation(user, product, quantity: int = 1) -> Order:
    """Create an order directly (bypassing checkout API) with an ACTIVE reservation.

    This helper lets tests set up the pre-payment state without triggering the
    checkout payment orchestration, preserving the ability to test the
    /api/v1/payments/ endpoint in isolation.
    """
    order = create_valid_order(user=user, customer_email=user.email)
    reserve_for_checkout(
        order=order,
        items=[{"product_id": product.id, "quantity": quantity}],
    )
    return order


@pytest.mark.django_db
def test_checkout_creates_active_inventory_reservations(auth_client, user):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    # cart add item
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )

    # checkout -> COD deferred flow: reservations stay ACTIVE until explicit payment
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    # After deferred COD checkout the payment is PENDING and reservations remain ACTIVE.
    # Commitment happens only after explicit POST /payments/ confirmation.
    reservations = InventoryReservation.objects.filter(order_id=order_id)
    assert reservations.exists()
    assert all(
        r.status == InventoryReservation.Status.ACTIVE for r in reservations)

    r = reservations.get(product_id=product.id)
    assert r.quantity == 2
    assert r.committed_at is None


@pytest.mark.django_db
def test_payment_success_commits_reservations_and_decrements_stock(auth_client, user):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    # Create order + reservation directly (bypassing checkout auto-payment)
    # so we can test the payment endpoint in isolation.
    order = _create_order_with_reservation(user, product, quantity=2)
    order_id = order.id

    # pay success via the manual dev endpoint
    pay_resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order_id, "result": "success"},
        format="json",
    )
    assert pay_resp.status_code == 201
    assert pay_resp.json()["status"] == "SUCCESS"

    product.refresh_from_db()
    order = Order.objects.get(id=order_id)
    reservations = InventoryReservation.objects.filter(order_id=order_id)

    assert order.status == Order.Status.PAID
    assert reservations.exists()
    assert all(
        r.status == InventoryReservation.Status.COMMITTED for r in reservations)
    assert all(r.committed_at is not None for r in reservations)

    # physical stock decrement happens on commit
    assert product.stock_quantity == 8


@pytest.mark.django_db
def test_payment_fail_marks_order_payment_failed_and_releases_reservations(auth_client, user):
    """
    Expected behaviour:
    - payment fail transitions order to PAYMENT_FAILED (retryable)
    - reservations are RELEASED immediately on failure, freeing stock for
      new checkout attempts (prevents stale reservations causing 409)
    - physical stock is NOT decremented
    """
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    # Create order + reservation directly (bypassing checkout auto-payment).
    order = _create_order_with_reservation(user, product)
    order_id = order.id

    pay_resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order_id, "result": "fail"},
        format="json",
    )
    assert pay_resp.status_code == 201
    assert pay_resp.json()["status"] == "FAILED"

    product.refresh_from_db()
    order = Order.objects.get(id=order_id)
    reservations = InventoryReservation.objects.filter(order_id=order_id)

    assert order.status == Order.Status.PAYMENT_FAILED
    assert order.cancel_reason == Order.CancelReason.PAYMENT_FAILED
    assert reservations.exists()
    assert all(
        r.status == InventoryReservation.Status.RELEASED for r in reservations)

    # stock not decremented (reservations released, not committed)
    assert product.stock_quantity == 10

    # one failed payment attempt recorded
    assert Payment.objects.filter(order_id=order_id).count() == 1
    assert Payment.objects.filter(
        order_id=order_id, status=Payment.Status.FAILED).count() == 1


@pytest.mark.django_db
def test_payment_retry_creates_new_attempt_and_succeeds(auth_client, user):
    """
    Expected behaviour:
    - first payment attempt fails -> order PAYMENT_FAILED, reservations RELEASED
    - second attempt succeeds -> new Payment row is created, order PAID
    - stock is NOT decremented on retry because reservations were already
      released on failure (dev-only DevFake scenario; CARD flow retries
      go through a fresh checkout with new reservations instead)
    """
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    # Create order + reservation directly (bypassing checkout auto-payment).
    order = _create_order_with_reservation(user, product)
    order_id = order.id

    # attempt 1: fail
    r1 = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order_id, "result": "fail"},
        format="json",
    )
    assert r1.status_code == 201
    assert r1.json()["status"] == "FAILED"

    order = Order.objects.get(id=order_id)
    assert order.status == Order.Status.PAYMENT_FAILED

    reservations = InventoryReservation.objects.filter(order_id=order_id)
    assert reservations.exists()
    # Reservations are released on payment failure to free stock for new
    # checkout attempts.  The retry path does not re-create reservations.
    assert all(
        r.status == InventoryReservation.Status.RELEASED for r in reservations)

    assert Payment.objects.filter(order_id=order_id).count() == 1
    assert Payment.objects.filter(
        order_id=order_id, status=Payment.Status.FAILED).count() == 1

    # attempt 2: success (new payment row)
    r2 = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order_id, "result": "success"},
        format="json",
    )
    assert r2.status_code == 201
    assert r2.json()["status"] == "SUCCESS"

    product.refresh_from_db()
    order.refresh_from_db()
    reservations = InventoryReservation.objects.filter(order_id=order_id)

    assert order.status == Order.Status.PAID
    # Reservations remain RELEASED — commit_reservations_for_paid finds no
    # ACTIVE rows and the fallback order.status = PAID path is used instead.
    assert all(
        r.status == InventoryReservation.Status.RELEASED for r in reservations)
    # Stock is NOT decremented because there were no ACTIVE reservations to
    # commit (they were released on the prior failure).
    assert product.stock_quantity == 10

    assert Payment.objects.filter(order_id=order_id).count() == 2
    assert Payment.objects.filter(
        order_id=order_id, status=Payment.Status.SUCCESS).count() == 1


@pytest.mark.django_db
def test_checkout_prevents_oversell_via_active_reservation_sum(auth_client, user):
    """
    Availability is physical stock - SUM(ACTIVE reservations).
    First reservation holds the last unit (ACTIVE, no stock decrement).
    Second checkout must fail with OUT_OF_STOCK at checkout time.
    """
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=1,
        is_active=True,
    )

    # Reserve the last unit directly (no auto-payment, no stock decrement).
    # ACTIVE reservation ties up the unit for availability purposes.
    first_order = _create_order_with_reservation(user, product)
    assert InventoryReservation.objects.filter(
        order_id=first_order.id, status=InventoryReservation.Status.ACTIVE).exists()

    # Second attempt: add to cart (physical stock=1 → add succeeds),
    # but checkout availability = stock - active = 1 - 1 = 0 → OUT_OF_STOCK
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    r2 = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )

    assert r2.status_code in (400, 409)
    assert r2.json().get("code") == "OUT_OF_STOCK"
