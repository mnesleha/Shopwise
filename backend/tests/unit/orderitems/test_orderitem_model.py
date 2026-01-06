from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from orders.models import Order
from orderitems.models import OrderItem
from products.models import Product
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_orderitem_must_have_order():

    User = get_user_model()
    user = User.objects.create_user(email="user1@example.com", password="pass")
    product = Product.objects.create(
        name="Phone",
        price=1000,
        stock_quantity=10,
        is_active=True,
    )

    item = OrderItem(
        order=None,
        product=product,
        quantity=1,
        price_at_order_time=1000,
    )

    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.mark.django_db
def test_orderitem_must_have_product():

    User = get_user_model()
    user = User.objects.create_user(email="user2@example.com", password="pass")
    order = Order.objects.create(user=user)

    item = OrderItem(
        order=order,
        product=None,
        quantity=1,
        price_at_order_time=1000,
    )

    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.mark.django_db
def test_orderitem_quantity_must_be_positive():

    User = get_user_model()
    user = User.objects.create_user(email="user3@example.com", password="pass")
    order = Order.objects.create(user=user)
    product = Product.objects.create(
        name="Laptop",
        price=2000,
        stock_quantity=5,
        is_active=True,
    )

    item = OrderItem(
        order=order,
        product=product,
        quantity=0,
        price_at_order_time=2000,
    )

    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.mark.django_db
def test_orderitem_price_snapshot_allows_zero():
    User = get_user_model()
    user = User.objects.create_user(email="user4@example.com", password="pass")
    order = Order.objects.create(user=user)
    product = Product.objects.create(
        name="Tablet",
        price=Decimal("500.00"),
        stock_quantity=10,
        is_active=True,
    )

    item = OrderItem(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("0.00"),
    )

    # should NOT raise
    item.full_clean()


@pytest.mark.django_db
def test_orderitem_price_snapshot_rejects_negative():
    User = get_user_model()
    user = User.objects.create_user(email="user5@example.com", password="pass")
    order = Order.objects.create(user=user)
    product = Product.objects.create(
        name="Tablet",
        price=Decimal("500.00"),
        stock_quantity=10,
        is_active=True,
    )

    item = OrderItem(
        order=order,
        product=product,
        quantity=1,
        price_at_order_time=Decimal("-0.01"),
    )

    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.mark.django_db
def test_valid_orderitem_is_valid():

    User = get_user_model()
    user = User.objects.create_user(email="user5@example.com", password="pass")
    order = Order.objects.create(user=user)
    product = Product.objects.create(
        name="Camera",
        price=800,
        stock_quantity=3,
        is_active=True,
    )

    item = OrderItem(
        order=order,
        product=product,
        quantity=2,
        price_at_order_time=800,
    )

    item.full_clean()  # should not raise
