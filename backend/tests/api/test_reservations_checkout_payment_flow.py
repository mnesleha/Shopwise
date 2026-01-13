import pytest
from django.utils import timezone

from orders.models import Order, InventoryReservation
from products.models import Product
from tests.conftest import checkout_payload, create_order_via_checkout


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

    # checkout -> should create order + ACTIVE reservation(s)
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    reservations = InventoryReservation.objects.filter(order_id=order_id)
    assert reservations.exists()
    assert all(
        r.status == InventoryReservation.Status.ACTIVE for r in reservations)

    r = reservations.get(product_id=product.id)
    assert r.quantity == 2
    assert r.expires_at is not None
    assert r.expires_at > timezone.now()


@pytest.mark.django_db
def test_payment_success_commits_reservations_and_decrements_stock(auth_client, user):
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    # checkout with qty=2 (uses existing helper)
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )
    checkout_resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    assert checkout_resp.status_code == 201
    order_id = checkout_resp.json()["id"]

    # pay success
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
def test_payment_fail_releases_reservations_and_cancels_order(auth_client, user):
    """
    Expected behaviour:
    - payment fail cancels order (CREATED -> CANCELLED, reason PAYMENT_FAILED)
    - reservations are released (ACTIVE -> RELEASED, release_reason PAYMENT_FAILED)
    - physical stock is NOT decremented
    """
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    order_data = create_order_via_checkout(
        auth_client, product, customer_email=user.email)
    order_id = order_data["id"]

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

    assert order.status == Order.Status.CANCELLED
    assert order.cancel_reason == Order.CancelReason.PAYMENT_FAILED
    assert reservations.exists()
    assert all(
        r.status == InventoryReservation.Status.RELEASED for r in reservations)
    assert all(r.released_at is not None for r in reservations)
    assert all(r.release_reason ==
               InventoryReservation.ReleaseReason.PAYMENT_FAILED for r in reservations)

    # stock not decremented
    assert product.stock_quantity == 10


@pytest.mark.django_db
def test_checkout_prevents_oversell_via_active_reservation_sum(auth_client, user):
    """
    Availability is physical stock - SUM(ACTIVE reservations).
    First checkout reserves the last unit, second checkout must fail with OUT_OF_STOCK.
    """
    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=1,
        is_active=True,
    )

    # First checkout reserves the last unit
    o1 = create_order_via_checkout(
        auth_client, product, customer_email=user.email)
    assert InventoryReservation.objects.filter(
        order_id=o1["id"], status=InventoryReservation.Status.ACTIVE).exists()

    # Second attempt: new cart session -> for simplicity, just add again and checkout
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
    # Your error contract should expose code OUT_OF_STOCK
    assert r2.json().get("code") == "OUT_OF_STOCK"
