import os
from decimal import Decimal
from discounts.models import Discount
import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from rest_framework.test import APIClient
from products.models import Product
from discounts.models import Discount
from orders.models import Order
from orderitems.models import OrderItem


def _wants_mysql(args: list[str]) -> bool:
    """Heuristika: pokud -m obsahuje mysql, jedeme MySQL settings."""
    if "-m" not in args:
        return False
    i = args.index("-m")
    if i + 1 >= len(args):
        return False
    expr = args[i + 1]
    # expr může být: "mysql", "mysql and not slow", "not sqlite and mysql", atd.
    return "mysql" in expr.split() or "mysql" in expr


def pytest_load_initial_conftests(early_config, parser, args):
    if _wants_mysql(args):
        # pokud uživatel nedal explicitně --ds, doplníme ho
        if not any(a.startswith("--ds=") for a in args) and "--ds" not in args:
            args.append("--ds=config.settings.local")

        # pro jistotu nastavíme i env (někdy se hodí pro code, co čte env přímo)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                              "config.settings.local")


@pytest.fixture(autouse=True)
def print_mysql_db_identity(request, db):
    if request.node.get_closest_marker("mysql"):
        print("\n--- MYSQL TEST DB INFO ---")
        print("ENGINE:", connection.settings_dict["ENGINE"])
        print("NAME:", connection.settings_dict["NAME"])
        print("HOST:", connection.settings_dict.get("HOST"))
        print("PORT:", connection.settings_dict.get("PORT"))
        print("VENDOR:", connection.vendor)

        if connection.vendor == "mysql":
            with connection.cursor() as c:
                c.execute("select database(), @@hostname, @@port")
                print("DB says:", c.fetchone())


# def pytest_collection_modifyitems(config, items):
#     use_mysql = config.getoption("-m") and "mysql" in config.getoption("-m")

#     if use_mysql:
#         os.environ["DJANGO_SETTINGS_MODULE"] = "settings.local"


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
def order_factory(db):
    """
    Factory for creating orders with a single order item.
    Explicitly sets snapshot pricing fields to avoid dependency on pricing service.

    Usage:
        order = order_factory(user=user)
        order = order_factory(user=user, status=Order.Status.CREATED)
        order = order_factory(user=user, quantity=2, unit_price="100.00")
    """
    def _create(
        *,
        user,
        status=Order.Status.CREATED,
        quantity=1,
        unit_price="100.00",
        line_total=None,
        discount_type=None,
        discount_value=None,
    ):
        product = Product.objects.create(
            name="Factory product",
            price=Decimal(unit_price),
            stock_quantity=10,
            is_active=True,
        )

        order = Order.objects.create(
            user=user,
            status=status,
        )

        if line_total is None:
            line_total = Decimal(unit_price) * quantity

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price_at_order_time=Decimal(unit_price),
            line_total_at_order_time=Decimal(line_total),
            price_at_order_time=Decimal(line_total),  # legacy compatibility
            applied_discount_type_at_order_time=discount_type,
            applied_discount_value_at_order_time=(
                Decimal(discount_value) if discount_value is not None else None
            ),
        )

        return order

    return _create


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
