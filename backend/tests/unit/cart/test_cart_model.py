from django.forms import ValidationError
import pytest
from django.contrib.auth.models import User
from carts.models import Cart


@pytest.mark.django_db
def test_user_can_have_only_one_active_cart():
    user = User.objects.create_user(username="u1")

    Cart.objects.create(user=user)

    with pytest.raises(Exception):
        Cart.objects.create(user=user)


@pytest.mark.django_db
def test_user_cannot_have_two_active_carts():
    user = User.objects.create_user(username="testuser")

    Cart.objects.create(
        user=user,
        status=Cart.Status.ACTIVE,
    )

    second_cart = Cart(
        user=user,
        status=Cart.Status.ACTIVE,
    )

    with pytest.raises(ValidationError):
        second_cart.save()


@pytest.mark.django_db
def test_user_can_have_converted_and_active_cart():
    user = User.objects.create_user(username="testuser")

    Cart.objects.create(
        user=user,
        status=Cart.Status.CONVERTED,
    )

    cart = Cart.objects.create(
        user=user,
        status=Cart.Status.ACTIVE,
    )

    assert cart.status == Cart.Status.ACTIVE
