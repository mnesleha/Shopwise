import pytest
from orders.models import Order
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from tests.conftest import checkout_payload, create_valid_order


@pytest.mark.django_db
def test_order_created_with_default_status():

    User = get_user_model()
    user = User.objects.create_user(
        email="testuser1@example.com",
        password="password",
    )

    order = create_valid_order(user=user)

    assert order.status == Order.Status.CREATED


@pytest.mark.skip(reason="User is optional until Cart is introduced")
@pytest.mark.django_db
def test_order_must_have_user():

    order = Order(user=None)

    with pytest.raises(Exception):
        order.full_clean()


@pytest.mark.django_db
def test_order_invalid_status_is_rejected():

    User = get_user_model()
    user = User.objects.create_user(
        email="testuser2@example.com",
        password="password",
    )

    payload = checkout_payload(customer_email=user.email)
    order = Order(
        user=user,
        status="INVALID",
        customer_email=payload["customer_email"],
        shipping_name=payload["shipping_name"],
        shipping_address_line1=payload["shipping_address_line1"],
        shipping_address_line2=payload["shipping_address_line2"],
        shipping_city=payload["shipping_city"],
        shipping_postal_code=payload["shipping_postal_code"],
        shipping_country=payload["shipping_country"],
        shipping_phone=payload["shipping_phone"],
        billing_same_as_shipping=payload["billing_same_as_shipping"],
    )

    with pytest.raises(ValidationError):
        order.full_clean()
