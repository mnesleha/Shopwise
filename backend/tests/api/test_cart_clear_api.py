"""
Tests for DELETE /api/v1/cart/ — clear all items from the active cart.

Contract:
- Authenticated user: clears all items, returns 204.
- Anonymous cart (by token): clears all items, returns 204.
- Empty / non-existent cart: still returns 204 (idempotent).
- Cart row is preserved; cart remains retrievable as an empty active cart.
"""

import pytest
from rest_framework.test import APIClient

from carts.models import Cart, CartItem
from products.models import Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product(**kwargs) -> Product:
    defaults = {"name": "Widget", "price": "9.99", "stock_quantity": 100, "is_active": True}
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def _add_item(client: APIClient, product: Product, quantity: int = 1) -> None:
    res = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )
    assert res.status_code in (200, 201), res.content


# ---------------------------------------------------------------------------
# Authenticated user tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_clear_cart_authenticated_returns_204(auth_client, user):
    """DELETE /cart/ clears items and returns 204 for an authenticated user."""
    product = _make_product()
    _add_item(auth_client, product)

    assert CartItem.objects.filter(cart__user=user).count() == 1

    res = auth_client.delete("/api/v1/cart/")

    assert res.status_code == 204
    assert CartItem.objects.filter(cart__user=user).count() == 0


@pytest.mark.django_db
def test_clear_cart_authenticated_cart_row_preserved(auth_client, user):
    """Cart row must not be deleted — only items are removed."""
    product = _make_product()
    _add_item(auth_client, product)

    auth_client.delete("/api/v1/cart/")

    assert Cart.objects.filter(user=user, status=Cart.Status.ACTIVE).exists()


@pytest.mark.django_db
def test_clear_cart_authenticated_cart_retrievable_as_empty(auth_client, user):
    """After clearing, GET /cart/ returns an empty active cart (204 path idempotent)."""
    product = _make_product()
    _add_item(auth_client, product)

    auth_client.delete("/api/v1/cart/")

    res = auth_client.get("/api/v1/cart/")
    assert res.status_code in (200, 201)
    body = res.json()
    assert body["status"] == "ACTIVE"
    assert body["items"] == []


@pytest.mark.django_db
def test_clear_cart_authenticated_multiple_items(auth_client, user):
    """All items are removed in a single request."""
    p1 = _make_product(name="A")
    p2 = _make_product(name="B")
    p3 = _make_product(name="C")
    for p in [p1, p2, p3]:
        _add_item(auth_client, p)

    assert CartItem.objects.filter(cart__user=user).count() == 3

    res = auth_client.delete("/api/v1/cart/")

    assert res.status_code == 204
    assert CartItem.objects.filter(cart__user=user).count() == 0


# ---------------------------------------------------------------------------
# Empty / non-existent cart (idempotent)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_clear_cart_no_cart_returns_204(auth_client, user):
    """If no active cart exists at all, DELETE still returns 204."""
    assert not Cart.objects.filter(user=user).exists()

    res = auth_client.delete("/api/v1/cart/")

    assert res.status_code == 204


@pytest.mark.django_db
def test_clear_cart_empty_cart_returns_204(auth_client, user):
    """If the active cart exists but has no items, DELETE returns 204."""
    Cart.objects.create(user=user, status=Cart.Status.ACTIVE)

    res = auth_client.delete("/api/v1/cart/")

    assert res.status_code == 204


# ---------------------------------------------------------------------------
# Anonymous cart tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_clear_cart_anonymous_by_cookie_returns_204():
    """Anonymous cart identified by cookie: items are cleared, 204 returned."""
    client = APIClient()
    product = _make_product()

    # Create anonymous cart with an item; cookie is set automatically
    add = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    assert add.status_code == 201, add.content
    assert "cart_token" in add.cookies

    # Read the cart id from GET to confirm item exists
    get_res = client.get("/api/v1/cart/")
    cart_id = get_res.json()["id"]
    assert CartItem.objects.filter(cart_id=cart_id).count() == 1

    res = client.delete("/api/v1/cart/")

    assert res.status_code == 204
    assert CartItem.objects.filter(cart_id=cart_id).count() == 0


@pytest.mark.django_db
def test_clear_cart_anonymous_by_header_returns_204():
    """Anonymous cart identified by X-Cart-Token header: items are cleared, 204 returned."""
    client_a = APIClient()
    product = _make_product()

    add = client_a.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )
    assert add.status_code == 201, add.content
    token = add.cookies["cart_token"].value

    # Use a fresh client with header-based token
    client_b = APIClient()
    res = client_b.delete(
        "/api/v1/cart/",
        HTTP_X_CART_TOKEN=token,
    )

    assert res.status_code == 204

    cart = Cart.objects.filter(status=Cart.Status.ACTIVE).first()
    assert cart is not None
    assert CartItem.objects.filter(cart=cart).count() == 0


@pytest.mark.django_db
def test_clear_cart_anonymous_no_token_returns_204():
    """Anonymous request with no cart token: no cart to clear, still 204."""
    client = APIClient()

    res = client.delete("/api/v1/cart/")

    assert res.status_code == 204


@pytest.mark.django_db
def test_clear_cart_anonymous_cart_row_preserved():
    """Cart row must not be deleted after clearing an anonymous cart."""
    client = APIClient()
    product = _make_product()

    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    client.delete("/api/v1/cart/")

    assert Cart.objects.filter(status=Cart.Status.ACTIVE).exists()
