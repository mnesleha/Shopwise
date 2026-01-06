import pytest
from django.contrib.auth import get_user_model
from carts.models import Cart, CartItem
from products.models import Product


@pytest.mark.django_db
def test_cart_item_quantity_must_be_positive():
    User = get_user_model()
    user = User.objects.create_user(email="u1@example.com", password="pass")
    cart = Cart.objects.create(user=user)

    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    with pytest.raises(Exception):
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=0,
            price_at_add_time=product.price,
        )
