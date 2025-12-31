from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient

from discounts.models import Discount
from orders.models import Order
from orderitems.models import OrderItem
from products.models import Product


@pytest.fixture
def user():
    return User.objects.create_user(
        username="testuser",
        password="pass1234",
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def product():
    return Product.objects.create(
        name="Test Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )


@pytest.fixture
def order(db, user):
    """
    Create an Order with one OrderItem using pricing snapshot fields.
    Suitable for unit tests and API tests.
    """
    product = Product.objects.create(
        name="Test product",
        price=Decimal("100.00"),
        stock_quantity=10,
        is_active=True,
    )

    order = Order.objects.create(
        user=user,
        status=Order.Status.CREATED,
    )

    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        unit_price_at_order_time=Decimal("100.00"),
        line_total_at_order_time=Decimal("80.00"),
        price_at_order_time=Decimal("80.00"),  # legacy compatibility
        applied_discount_type_at_order_time="PERCENT",
        applied_discount_value_at_order_time=Decimal("20.00"),
    )

    return order


@pytest.fixture
def order_without_discount(db, user):
    product = Product.objects.create(
        name="No discount product",
        price=Decimal("50.00"),
        stock_quantity=10,
        is_active=True,
    )

    order = Order.objects.create(
        user=user,
        status=Order.Status.CREATED,
    )

    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        unit_price_at_order_time=Decimal("50.00"),
        line_total_at_order_time=Decimal("50.00"),
        price_at_order_time=Decimal("50.00"),
    )

    return order


@pytest.fixture(scope="session", autouse=True)
def seed_test_data(django_db_setup, django_db_blocker):
    """
    Seed deterministic test data once per test session.
    Does NOT flush DB, preserves superuser.
    """

    with django_db_blocker.unblock():
        call_command("seed_test_data", reset=True)


@pytest.fixture
def fixed_discount(db):
    """
    Create an active FIXED discount targeting a product.
    Usage:
        fixed_discount(product=product, value="150.00")
    """
    def _create(*, product, value, name="Fixed discount"):
        return Discount.objects.create(
            name=name,
            discount_type=Discount.FIXED,
            value=value,
            is_active=True,
            product=product,
        )
    return _create


@pytest.fixture
def percent_discount(db):
    """
    Create an active PERCENT discount targeting a product.
    Usage:
        percent_discount(product=product, value="10.00")
    """
    def _create(*, product, value, name="Percent discount"):
        return Discount.objects.create(
            name=name,
            discount_type=Discount.PERCENT,
            value=value,
            is_active=True,
            product=product,
        )
    return _create


def create_order_via_checkout(auth_client, product):
    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 201

    data = response.json()
    return data
