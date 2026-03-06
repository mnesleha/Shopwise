"""
Tests for the login refactor (no cart/order side-effects) and the two new
post-login settling endpoints:

  POST /api/v1/cart/merge/
  POST /api/v1/orders/claim/
"""

import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

LOGIN_URL = "/api/v1/auth/login/"
CART_MERGE_URL = "/api/v1/cart/merge/"
ORDERS_CLAIM_URL = "/api/v1/orders/claim/"
REGISTER_URL = "/api/v1/auth/register/"

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(email="user@example.com", password="Passw0rd!123", verified=False):
    user = User.objects.create_user(email=email, password=password)
    if verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])
    return user


def _login(client, email="user@example.com", password="Passw0rd!123"):
    return client.post(LOGIN_URL, {"email": email, "password": password}, format="json")


# ---------------------------------------------------------------------------
# A) Login no longer triggers side effects
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@patch("api.views.auth.claim_guest_orders_for_user")
@patch("api.views.auth.merge_or_adopt_guest_cart")
def test_login_does_not_call_merge_or_adopt_guest_cart(mock_merge, mock_claim):
    """Login must not call merge_or_adopt_guest_cart — that's now /cart/merge/."""
    _create_user()
    client = APIClient()
    resp = _login(client)
    assert resp.status_code == 200
    mock_merge.assert_not_called()


@pytest.mark.django_db
@patch("api.views.auth.claim_guest_orders_for_user")
@patch("api.views.auth.merge_or_adopt_guest_cart")
def test_login_does_not_call_claim_guest_orders(mock_merge, mock_claim):
    """Login must not call claim_guest_orders_for_user — that's now /orders/claim/."""
    _create_user(verified=True)
    client = APIClient()
    resp = _login(client)
    assert resp.status_code == 200
    mock_claim.assert_not_called()


@pytest.mark.django_db
def test_login_response_does_not_include_claimed_orders():
    """Login response must only contain token fields — no claimed_orders."""
    _create_user(verified=True)
    client = APIClient()
    resp = _login(client)
    assert resp.status_code == 200
    body = resp.json()
    assert "claimed_orders" not in body
    assert "access" in body
    assert "refresh" in body


# ---------------------------------------------------------------------------
# B) POST /api/v1/cart/merge/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_cart_merge_requires_authentication():
    """Anonymous request must get 401."""
    client = APIClient()
    resp = client.post(CART_MERGE_URL, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
@patch("api.views.auth.merge_or_adopt_guest_cart")
def test_cart_merge_no_guest_token_returns_204(mock_merge):
    """Authenticated user with no cart token → 204 and service called once."""
    _create_user()
    client = APIClient()
    resp = _login(client)
    assert resp.status_code == 200

    merge_resp = client.post(CART_MERGE_URL, format="json")
    assert merge_resp.status_code == 204
    mock_merge.assert_called_once()


@pytest.mark.django_db
@patch(
    "api.views.auth.merge_or_adopt_guest_cart",
    side_effect=lambda **kwargs: None,  # no-op: success
)
def test_cart_merge_clears_cart_token_cookie(mock_merge):
    """On success the response must expire the cart_token cookie."""
    _create_user()
    client = APIClient()
    _login(client)

    merge_resp = client.post(CART_MERGE_URL, format="json")
    assert merge_resp.status_code == 204
    # Django sets Max-Age=0 (or 'expires' in the past) to delete a cookie.
    assert "cart_token" in merge_resp.cookies


@pytest.mark.django_db
@patch("api.views.auth.merge_or_adopt_guest_cart")
def test_cart_merge_stock_conflict_returns_409(mock_merge):
    """If merge raises CartMergeStockConflict the endpoint must return 409."""
    from carts.services.merge import CartMergeStockConflict

    mock_merge.side_effect = CartMergeStockConflict()

    _create_user()
    client = APIClient()
    _login(client)

    merge_resp = client.post(CART_MERGE_URL, format="json")
    assert merge_resp.status_code == 409
    body = merge_resp.json()
    assert body.get("code") == "CART_MERGE_STOCK_CONFLICT"


# ---------------------------------------------------------------------------
# C) POST /api/v1/orders/claim/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_orders_claim_requires_authentication():
    """Anonymous request must get 401."""
    client = APIClient()
    resp = client.post(ORDERS_CLAIM_URL, format="json")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_orders_claim_unverified_user_returns_zero():
    """Unverified user must get claimed_orders=0 without hitting the service."""
    _create_user(verified=False)
    client = APIClient()
    _login(client)

    with patch("api.views.auth.claim_guest_orders_for_user") as mock_claim:
        resp = client.post(ORDERS_CLAIM_URL, format="json")

    assert resp.status_code == 200
    assert resp.json()["claimed_orders"] == 0
    mock_claim.assert_not_called()


@pytest.mark.django_db
@patch("api.views.auth.claim_guest_orders_for_user", return_value=3)
def test_orders_claim_verified_user_returns_claimed_count(mock_claim):
    """Verified user must get the count returned by the service."""
    _create_user(verified=True)
    client = APIClient()
    _login(client)

    resp = client.post(ORDERS_CLAIM_URL, format="json")
    assert resp.status_code == 200
    assert resp.json()["claimed_orders"] == 3
    mock_claim.assert_called_once()


# ---------------------------------------------------------------------------
# Integration tests — real DB, no mocks
# These replace the old login-triggered side-effect tests that were deleted.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_cart_merge_integration_sums_quantities():
    """
    POST /cart/merge/ with a real guest cart merges quantities into the user
    cart and returns 204.  Mirrors the deleted
    test_login_merges_guest_cart_into_existing_user_cart.
    """
    from carts.models import Cart, CartItem
    from products.models import Product

    product = Product.objects.create(
        name="Merge Product", price=50, stock_quantity=20, is_active=True
    )

    user = _create_user()

    # User already has 2x product in their active cart.
    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(
        cart=user_cart, product=product, quantity=2, price_at_add_time=product.price
    )

    # Guest adds 3x the same product.
    guest_client = APIClient()
    add = guest_client.post(
        "/api/v1/cart/items/", {"product_id": product.id, "quantity": 3}, format="json"
    )
    assert add.status_code == 201, add.content
    cart_token = add.cookies["cart_token"].value

    # Log in and call /cart/merge/ with the guest token in the header.
    login_resp = _login(guest_client)
    assert login_resp.status_code == 200
    access = login_resp.json()["access"]

    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    merge_resp = authed.post(
        CART_MERGE_URL, HTTP_X_CART_TOKEN=cart_token, format="json"
    )
    assert merge_resp.status_code == 204

    # Cart should now have 2 + 3 = 5 items for that product.
    cart_resp = authed.get("/api/v1/cart/")
    assert cart_resp.status_code in (200, 201)
    cart = cart_resp.json()
    assert cart["id"] == user_cart.id
    items = cart["items"]
    assert len(items) == 1
    assert items[0]["product"]["id"] == product.id
    assert items[0]["quantity"] == 5


@pytest.mark.django_db
@pytest.mark.sqlite
def test_cart_merge_integration_stock_conflict_returns_409():
    """
    POST /cart/merge/ returns 409 when merging would exceed available stock.
    Mirrors the deleted test_login_merge_conflict_when_exceeds_stock.
    """
    from carts.models import Cart, CartItem
    from products.models import Product

    product = Product.objects.create(
        name="Stock Limited", price=10, stock_quantity=4, is_active=True
    )

    user = _create_user()

    # User cart already holds 3 units; stock is 4.
    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(
        cart=user_cart, product=product, quantity=3, price_at_add_time=product.price
    )

    # Guest adds 2 more — 3 + 2 = 5 > stock(4) → conflict.
    guest_client = APIClient()
    add = guest_client.post(
        "/api/v1/cart/items/", {"product_id": product.id, "quantity": 2}, format="json"
    )
    assert add.status_code == 201, add.content
    cart_token = add.cookies["cart_token"].value

    login_resp = _login(guest_client)
    assert login_resp.status_code == 200
    access = login_resp.json()["access"]

    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    merge_resp = authed.post(
        CART_MERGE_URL, HTTP_X_CART_TOKEN=cart_token, format="json"
    )
    assert merge_resp.status_code == 409
    body = merge_resp.json()
    assert body.get("code") == "CART_MERGE_STOCK_CONFLICT"


@pytest.mark.django_db
def test_orders_claim_integration_assigns_guest_orders():
    """
    POST /orders/claim/ assigns guest orders whose contact email matches the
    verified user's email.  Mirrors the deleted
    test_login_claims_guest_orders_for_verified_user.
    """
    from orders.models import Order
    from tests.conftest import checkout_payload

    # Create a guest order before the user account exists.
    guest_order = Order.objects.create(
        user=None, **checkout_payload(customer_email="claimer@example.com")
    )

    user = _create_user(email="claimer@example.com", verified=True)

    client = APIClient()
    login_resp = _login(client, email="claimer@example.com")
    assert login_resp.status_code == 200
    access = login_resp.json()["access"]

    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    claim_resp = authed.post(ORDERS_CLAIM_URL, format="json")
    assert claim_resp.status_code == 200
    assert claim_resp.json()["claimed_orders"] >= 1

    guest_order.refresh_from_db()
    assert guest_order.user_id == user.id
    assert guest_order.is_claimed is True
