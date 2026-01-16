import pytest
from carts.models import ActiveCart, Cart


@pytest.mark.django_db
def test_auth_user_get_cart_creates_pointer_and_is_stable(auth_client, user):
    r1 = auth_client.get("/api/v1/cart/")
    assert r1.status_code == 200
    cart_id_1 = r1.json()["id"]

    r2 = auth_client.get("/api/v1/cart/")
    assert r2.status_code == 200
    cart_id_2 = r2.json()["id"]

    assert cart_id_1 == cart_id_2

    ptr = ActiveCart.objects.get(user=user)
    assert ptr.cart_id == cart_id_1

    assert Cart.objects.filter(
        user=user, status=Cart.Status.ACTIVE).count() == 1
