import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone

from carts.models import Cart, CartItem
from products.models import Product

from carts.services.resolver import (
    extract_cart_token,
    hash_cart_token,
    get_active_anonymous_cart_by_token,
)
from carts.services.merge import merge_or_adopt_guest_cart, CartMergeStockConflict


@pytest.mark.django_db
def test_extract_cart_token_header_takes_precedence_over_cookie():
    rf = RequestFactory()
    req = rf.get("/")
    req.COOKIES["cart_token"] = "cookie-token"
    req.headers = {"X-Cart-Token": "header-token"}

    assert extract_cart_token(req) == "header-token"


@pytest.mark.django_db
def test_extract_cart_token_falls_back_to_cookie_when_no_header():
    rf = RequestFactory()
    req = rf.get("/")
    req.COOKIES["cart_token"] = "cookie-token"
    req.headers = {}

    assert extract_cart_token(req) == "cookie-token"


def test_hash_cart_token_returns_sha256_hex_digest():
    h = hash_cart_token("abc")
    assert isinstance(h, str)
    assert len(h) == 64
    # hex check
    int(h, 16)


@pytest.mark.django_db
def test_get_active_anonymous_cart_by_token_returns_none_when_not_found():
    assert get_active_anonymous_cart_by_token("missing") is None


@pytest.mark.django_db
def test_get_active_anonymous_cart_by_token_finds_active_anonymous_cart():
    token = "t1"
    token_hash = hash_cart_token(token)
    cart = Cart.objects.create(
        user=None, status=Cart.Status.ACTIVE, anonymous_token_hash=token_hash)

    found = get_active_anonymous_cart_by_token(token)
    assert found is not None
    assert found.id == cart.id


@pytest.mark.django_db
def test_merge_or_adopt_guest_cart_noop_on_none_or_empty_token():
    User = get_user_model()
    user = User.objects.create_user(
        email="noop@example.com", password="Passw0rd!123")

    merge_or_adopt_guest_cart(user=user, raw_token=None)
    merge_or_adopt_guest_cart(user=user, raw_token="")
    # treated as truthy in python, but may still be no-op later
    merge_or_adopt_guest_cart(user=user, raw_token="   ")

    # No carts should be created by this service alone
    assert Cart.objects.count() == 0


@pytest.mark.django_db
def test_adopt_guest_cart_when_user_has_no_active_cart():
    User = get_user_model()
    user = User.objects.create_user(
        email="adopt_svc@example.com", password="Passw0rd!123")

    p = Product.objects.create(
        name="P1", price=10, stock_quantity=10, is_active=True)

    raw_token = "guest-token-adopt"
    anon = Cart.objects.create(
        user=None,
        status=Cart.Status.ACTIVE,
        anonymous_token_hash=hash_cart_token(raw_token),
    )
    CartItem.objects.create(cart=anon, product=p,
                            quantity=2, price_at_add_time=p.price)

    merge_or_adopt_guest_cart(user=user, raw_token=raw_token)

    anon.refresh_from_db()
    assert anon.user_id == user.id
    assert anon.status == Cart.Status.ACTIVE
    assert anon.anonymous_token_hash is None
    assert anon.merged_into_cart_id is None
    assert anon.merged_at is None


@pytest.mark.django_db
def test_merge_guest_cart_into_existing_user_active_cart_sums_quantities():
    User = get_user_model()
    user = User.objects.create_user(
        email="merge_svc@example.com", password="Passw0rd!123")

    p = Product.objects.create(
        name="P2", price=10, stock_quantity=100, is_active=True)

    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(cart=user_cart, product=p,
                            quantity=2, price_at_add_time=p.price)

    raw_token = "guest-token-merge"
    anon = Cart.objects.create(
        user=None,
        status=Cart.Status.ACTIVE,
        anonymous_token_hash=hash_cart_token(raw_token),
    )
    CartItem.objects.create(cart=anon, product=p,
                            quantity=3, price_at_add_time=p.price)

    merge_or_adopt_guest_cart(user=user, raw_token=raw_token)

    # user cart quantity becomes 5
    merged_item = CartItem.objects.get(cart=user_cart, product=p)
    assert merged_item.quantity == 5

    # anon cart becomes MERGED terminal
    anon.refresh_from_db()
    assert anon.user_id is None
    assert anon.status == Cart.Status.MERGED
    assert anon.anonymous_token_hash is None
    assert anon.merged_into_cart_id == user_cart.id
    assert anon.merged_at is not None


@pytest.mark.django_db
def test_merge_raises_conflict_when_exceeds_stock():
    User = get_user_model()
    user = User.objects.create_user(
        email="conflict_svc@example.com", password="Passw0rd!123")

    p = Product.objects.create(
        name="P3", price=10, stock_quantity=4, is_active=True)

    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(cart=user_cart, product=p,
                            quantity=3, price_at_add_time=p.price)

    raw_token = "guest-token-conflict"
    anon = Cart.objects.create(
        user=None,
        status=Cart.Status.ACTIVE,
        anonymous_token_hash=hash_cart_token(raw_token),
    )
    CartItem.objects.create(cart=anon, product=p,
                            quantity=2, price_at_add_time=p.price)

    with pytest.raises(CartMergeStockConflict):
        merge_or_adopt_guest_cart(user=user, raw_token=raw_token)

    # Ensure no partial merge happened
    assert CartItem.objects.get(cart=user_cart, product=p).quantity == 3
    anon.refresh_from_db()
    assert anon.status == Cart.Status.ACTIVE


@pytest.mark.django_db
def test_extract_cart_token_empty_header_falls_back_to_cookie():
    rf = RequestFactory()
    # Django will expose this as "X-Cart-Token: " (empty value)
    req = rf.get("/", HTTP_X_CART_TOKEN="")
    req.COOKIES["cart_token"] = "cookie-token"

    assert extract_cart_token(req) == "cookie-token"
