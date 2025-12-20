import pytest
from orders.models import Order
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_order_created_with_default_status():

    User = get_user_model()
    user = User.objects.create_user(
        username="testuser",
        password="password",
    )

    order = Order.objects.create(user=user)

    assert order.status == Order.Status.CREATED


@pytest.mark.django_db
def test_order_must_have_user():

    order = Order(user=None)

    with pytest.raises(Exception):
        order.full_clean()


@pytest.mark.django_db
def test_order_invalid_status_is_rejected():

    User = get_user_model()
    user = User.objects.create_user(
        username="testuser2",
        password="password",
    )

    order = Order(
        user=user,
        status="INVALID",
    )

    with pytest.raises(ValidationError):
        order.full_clean()
