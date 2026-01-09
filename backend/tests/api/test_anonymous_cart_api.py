import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from carts.models import Cart, CartItem
from products.models import Product


CART_TOKEN_COOKIE = "cart_token"
CART_TOKEN_HEADER = "X-Cart-Token"


def _extract_cart_token_from_response(response) -> str:
    """
    Expect backend to set an HttpOnly cookie containing guest cart token.
    DRF test client exposes cookies via response.cookies.
    """
    assert CART_TOKEN_COOKIE in response.cookies, (
        f"Expected Set-Cookie '{CART_TOKEN_COOKIE}' to be present."
    )
    return response.cookies[CART_TOKEN_COOKIE].value


def _register_user(client: APIClient, *, email: str, password: str) -> dict:
    res = client.post(
        "/api/v1/auth/register/",
        {"email": email, "password": password,
            "first_name": "Guest", "last_name": "User"},
        format="json",
    )
    assert res.status_code == 201, res.content
    return res.json()


def _login_user(client: APIClient, *, email: str, password: str, cart_token: str | None = None) -> dict:
    headers = {}
    if cart_token:
        headers[f"HTTP_{CART_TOKEN_HEADER.replace('-', '_').upper()}"] = cart_token

    res = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
        **headers,
    )
    assert res.status_code == 200, res.content
    data = res.json()
    assert "access" in data and data["access"]
    return data


@pytest.mark.django_db
@pytest.mark.sqlite
def test_guest_add_item_sets_cookie_and_cart_is_persistent(product):
    """
    Guest adds an item without having a token yet:
    - backend creates guest cart
    - backend sets HttpOnly cookie cart_token
    - subsequent GET /cart returns same cart with items
    """
    client = APIClient()

    add = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )
    assert add.status_code == 201, add.content

    token = _extract_cart_token_from_response(add)

    # subsequent requests should reuse cookie automatically (same client)
    res = client.get("/api/v1/cart/")
    assert res.status_code in (200, 201), res.content
    cart = res.json()

    assert cart["status"] == "ACTIVE"
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 2
    assert cart["items"][0]["product"]["id"] == product.id

    # sanity: DB has exactly one ACTIVE cart without user (anonymous)
    assert Cart.objects.filter(status=Cart.Status.ACTIVE).count() == 1
    # (user=None will be introduced by anonymous cart implementation)


@pytest.mark.django_db
@pytest.mark.sqlite
def test_guest_can_use_header_token_instead_of_cookie(product):
    """
    Token transport:
    - First request sets cookie cart_token
    - A new client (no cookies) can still access the same cart via X-Cart-Token header
    """
    client = APIClient()

    add = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    assert add.status_code == 201, add.content
    token = _extract_cart_token_from_response(add)

    # New client, no cookie jar
    client2 = APIClient()
    res = client2.get(
        "/api/v1/cart/",
        **{f"HTTP_{CART_TOKEN_HEADER.replace('-', '_').upper()}": token},
    )
    assert res.status_code in (200, 201), res.content
    cart = res.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 1


@pytest.mark.django_db
@pytest.mark.sqlite
def test_guest_register_then_login_adopts_guest_cart(product):
    """
    Required flow:
    guest cart -> user register (still guest) -> user login -> guest cart becomes user's active cart.
    Expected: adoption (user had no active cart) => items preserved, token invalidated.
    """
    guest = APIClient()

    add = guest.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 3},
        format="json",
    )
    assert add.status_code == 201, add.content
    token = _extract_cart_token_from_response(add)

    email = "newuser@example.com"
    password = "Passw0rd!123"

    _register_user(guest, email=email, password=password)

    # login using the guest token (header is easiest for tests)
    tokens = _login_user(guest, email=email,
                         password=password, cart_token=token)

    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    res = authed.get("/api/v1/cart/")
    assert res.status_code in (200, 201), res.content
    cart = res.json()

    assert cart["status"] == "ACTIVE"
    assert len(cart["items"]) == 1
    assert cart["items"][0]["product"]["id"] == product.id
    assert cart["items"][0]["quantity"] == 3

    # Token should be invalid after adopt/merge:
    # Guest client using the old token should NOT see the user's cart anymore.
    guest2 = APIClient()
    res2 = guest2.get(
        "/api/v1/cart/",
        **{f"HTTP_{CART_TOKEN_HEADER.replace('-', '_').upper()}": token},
    )
    # Two acceptable behaviours:
    # A) create a new empty guest cart (200/201 with empty items)
    # B) explicit 404/401 for invalid token
    assert res2.status_code in (200, 201, 404, 401), res2.content
    if res2.status_code in (200, 201):
        assert res2.json()["items"] == []


@pytest.mark.django_db
@pytest.mark.sqlite
def test_login_merges_guest_cart_into_existing_user_cart(product):
    """
    If user already has an active cart, login should MERGE:
    - quantities summed per product
    - token invalidated
    """
    User = get_user_model()
    user = User.objects.create_user(
        email="merge@example.com", password="Passw0rd!123")

    # Create user's active cart with 2x product
    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(
        cart=user_cart,
        product=product,
        quantity=2,
        price_at_add_time=product.price,
    )

    # Guest cart has 3x same product
    guest = APIClient()
    add = guest.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 3},
        format="json",
    )
    assert add.status_code == 201, add.content
    token = _extract_cart_token_from_response(add)

    # Login merges into existing user cart => total 5
    tokens = _login_user(guest, email=user.email,
                         password="Passw0rd!123", cart_token=token)

    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    res = authed.get("/api/v1/cart/")
    assert res.status_code in (200, 201), res.content
    cart = res.json()

    assert cart["id"] == user_cart.id
    assert len(cart["items"]) == 1
    assert cart["items"][0]["product"]["id"] == product.id
    assert cart["items"][0]["quantity"] == 5


@pytest.mark.django_db
@pytest.mark.sqlite
def test_login_merge_conflict_when_exceeds_stock():
    """
    Merge policy requires a 409 Conflict when resulting quantity exceeds available stock.
    We test conflict on same product.
    """
    p = Product.objects.create(
        name="Stock Limited",
        price=10,
        stock_quantity=4,  # low stock to force conflict
        is_active=True,
    )

    User = get_user_model()
    user = User.objects.create_user(
        email="conflict@example.com", password="Passw0rd!123")

    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(cart=user_cart, product=p,
                            quantity=3, price_at_add_time=p.price)

    guest = APIClient()
    add = guest.post(
        "/api/v1/cart/items/",
        # 3 + 2 = 5 > stock(4) => conflict
        {"product_id": p.id, "quantity": 2},
        format="json",
    )
    assert add.status_code == 201, add.content
    token = _extract_cart_token_from_response(add)

    res = guest.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "Passw0rd!123"},
        format="json",
        **{f"HTTP_{CART_TOKEN_HEADER.replace('-', '_').upper()}": token},
    )
    assert res.status_code == 409, res.content
    body = res.json()

    # Unified error shape
    assert "code" in body and "message" in body
    # Suggested code (align final naming with your conventions)
    # e.g. CART_MERGE_STOCK_CONFLICT
    assert body["code"].isupper()
