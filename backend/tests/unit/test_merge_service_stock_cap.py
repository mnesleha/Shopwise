"""
Unit tests for merge service stock-capping logic.

These tests do NOT call any API endpoint — they call the service function
directly to verify stock-capping behaviour at the domain level.
"""

import pytest
from carts.models import Cart, CartItem
from carts.services.merge import merge_or_adopt_guest_cart
from carts.services.resolver import hash_cart_token
from products.models import Product


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_product(name="Widget", stock=10, price=9):
    return Product.objects.create(
        name=name, price=price, stock_quantity=stock, is_active=True
    )


def _make_guest_cart(token: str) -> Cart:
    return Cart.objects.create(
        anonymous_token_hash=hash_cart_token(token),
        status=Cart.Status.ACTIVE,
    )


def _add_item(cart: Cart, product: Product, qty: int) -> CartItem:
    return CartItem.objects.create(
        cart=cart, product=product, quantity=qty, price_at_add_time=product.price
    )


# ── adopt path ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_adopt_caps_quantity_to_stock(django_user_model):
    """ADOPT: guest cart qty > stock → item qty capped, STOCK_ADJUSTED warning emitted."""
    product = _make_product(stock=3)
    user = django_user_model.objects.create_user(
        email="user@example.com", password="P@ssw0rd"
    )

    guest_cart = _make_guest_cart("tok-a1")
    _add_item(guest_cart, product, qty=7)  # 7 > stock(3)

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-a1")

    assert report["performed"] is True
    assert report["result"] == "ADOPTED"
    warnings = report["warnings"]
    assert len(warnings) == 1
    assert warnings[0]["code"] == "STOCK_ADJUSTED"
    assert warnings[0]["product_id"] == product.id
    assert warnings[0]["requested"] == 7
    assert warnings[0]["applied"] == 3

    adopted_cart = Cart.objects.get(user=user, status=Cart.Status.ACTIVE)
    item = CartItem.objects.get(cart=adopted_cart, product=product)
    assert item.quantity == 3


@pytest.mark.django_db
def test_adopt_removes_zero_stock_item(django_user_model):
    """ADOPT: guest item where stock == 0 must be removed and warning applied=0 emitted."""
    product = _make_product(stock=0)
    user = django_user_model.objects.create_user(
        email="user2@example.com", password="P@ssw0rd"
    )

    guest_cart = _make_guest_cart("tok-a2")
    _add_item(guest_cart, product, qty=3)

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-a2")

    assert report["performed"] is True
    assert report["result"] == "ADOPTED"
    warnings = report["warnings"]
    assert len(warnings) == 1
    w = warnings[0]
    assert w["code"] == "STOCK_ADJUSTED"
    assert w["applied"] == 0

    # The zero-stock item must NOT appear in the new user cart.
    adopted_cart = Cart.objects.get(user=user, status=Cart.Status.ACTIVE)
    assert not CartItem.objects.filter(cart=adopted_cart, product=product).exists()


# ── merge path ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_merge_caps_merged_quantity_to_stock(django_user_model):
    """MERGE: user qty + guest qty > stock → summed qty capped, warning emitted."""
    product = _make_product(stock=4)
    user = django_user_model.objects.create_user(
        email="user3@example.com", password="P@ssw0rd"
    )

    # User already has 3 in cart; guest brings 3 more → would be 6, but stock=4.
    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    _add_item(user_cart, product, qty=3)

    guest_cart = _make_guest_cart("tok-m1")
    _add_item(guest_cart, product, qty=3)

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-m1")

    assert report["performed"] is True
    assert report["result"] == "MERGED"
    warnings = report["warnings"]
    assert len(warnings) == 1
    w = warnings[0]
    assert w["code"] == "STOCK_ADJUSTED"
    assert w["requested"] == 6
    assert w["applied"] == 4

    item = CartItem.objects.get(cart=user_cart, product=product)
    assert item.quantity == 4


@pytest.mark.django_db
def test_merge_no_warning_when_within_stock(django_user_model):
    """MERGE: summed quantity within stock → no warnings, quantities are summed."""
    product = _make_product(stock=20)
    user = django_user_model.objects.create_user(
        email="user4@example.com", password="P@ssw0rd"
    )

    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    _add_item(user_cart, product, qty=3)

    guest_cart = _make_guest_cart("tok-m2")
    _add_item(guest_cart, product, qty=5)

    report = merge_or_adopt_guest_cart(user=user, raw_token="tok-m2")

    assert report["performed"] is True
    assert report["result"] == "MERGED"
    assert report["warnings"] == []

    item = CartItem.objects.get(cart=user_cart, product=product)
    assert item.quantity == 8
