from django.forms import ValidationError
import pytest
from django.contrib.auth import get_user_model
from carts.services.active_cart_service import get_or_create_active_cart_for_user
from carts.models import Cart, ActiveCart


@pytest.mark.django_db
def test_user_can_have_only_one_active_cart():
    User = get_user_model()

    user = User.objects.create_user(email="u1@example.com", password="pass")

    cart1, created1 = get_or_create_active_cart_for_user(user)
    assert created1 is True
    assert ActiveCart.objects.filter(user=user).count() == 1
    assert ActiveCart.objects.get(user=user).cart_id == cart1.id

    cart2, created2 = get_or_create_active_cart_for_user(user)
    assert created2 is False
    assert cart2.id == cart1.id
    assert ActiveCart.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_user_cannot_have_two_active_carts():
    User = get_user_model()

    user = User.objects.create_user(
        email="testuser1@example.com", password="pass")

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
    User = get_user_model()

    user = User.objects.create_user(
        email="testuser2@example.com", password="pass")

    Cart.objects.create(
        user=user,
        status=Cart.Status.CONVERTED,
    )

    cart = Cart.objects.create(
        user=user,
        status=Cart.Status.ACTIVE,
    )

    assert cart.status == Cart.Status.ACTIVE
