import pytest
from unittest.mock import patch
from django.db import IntegrityError, connection
from django.urls import resolve, Resolver404
from orderitems.models import OrderItem
from orders.models import Order
from products.models import Product


@pytest.mark.mysql
def test_payments_route_exists_mysql():
    try:
        resolve("/api/v1/payments/")
    except Resolver404:
        pytest.fail(
            "Route /api/v1/payments/ not registered in this test environment")

# Transaction & isolation (checkout atomicity)


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_checkout_is_atomic_on_mysql(auth_client, user, product):
    """
    If OrderItem creation fails, Order must not be persisted.
    """
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    # Simulate DB-level failure (e.g. constraint / precision issue)
    with patch("orderitems.models.OrderItem.save", side_effect=Exception):
        response = auth_client.post("/api/v1/cart/checkout/")
        assert response.status_code in (409, 500)

    assert Order.objects.count() == 0
    assert OrderItem.objects.count() == 0


# Decimal precision & rounding persistence
@pytest.mark.mysql
@pytest.mark.django_db
def test_decimal_precision_round_trip_mysql(order):
    item = order.items.first()

    # Must persist exactly 2 decimals
    assert str(item.unit_price_at_order_time) == "100.00"
    assert str(item.line_total_at_order_time) == "80.00"


# Unique / FK constraints enforcement
@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_orderitem_requires_existing_order_mysql(db):
    product = Product.objects.create(
        name="P",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    with pytest.raises(IntegrityError):
        OrderItem.objects.create(
            order_id=999999,
            product=product,
            quantity=1,
            price_at_order_time=10,
        )

    # if the DB doesn't raise immediately, force constraint check now
    connection.check_constraints()

# Concurrency / race condition (checkout vs payment)


@pytest.mark.mysql
@pytest.mark.django_db(transaction=True)
def test_payment_double_submit_mysql(auth_client, user, order_factory):
    order = order_factory(user=user)

    payload = {"order_id": order.id, "result": "success"}

    r1 = auth_client.post("/api/v1/payments/", payload, format="json")
    r2 = auth_client.post("/api/v1/payments/", payload, format="json")

    assert Order.objects.filter(id=order.id, user=user).exists()
    order_db = Order.objects.get(id=order.id)

    assert Order.objects.filter(id=order.id, user=user).exists()

    assert r1.status_code == 201
    assert r2.status_code == 409


# Datetime & timezone precision
@pytest.mark.mysql
@pytest.mark.django_db
def test_order_created_at_precision_mysql(order):
    o = Order.objects.get(id=order.id)
    assert o.created_at.tzinfo is not None


# DB error maps to correct API error
@pytest.mark.mysql
@pytest.mark.django_db
def test_mysql_integrity_error_maps_to_api_error(auth_client):
    response = auth_client.post("/api/v1/payments/", {"order_id": 9999})
    assert response.status_code in (400, 404)
