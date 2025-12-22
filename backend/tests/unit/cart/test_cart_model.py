import pytest
from django.contrib.auth.models import User
from carts.models import Cart


@pytest.mark.django_db
def test_user_can_have_only_one_active_cart():
    user = User.objects.create_user(username="u1")

    Cart.objects.create(user=user)

    with pytest.raises(Exception):
        Cart.objects.create(user=user)
