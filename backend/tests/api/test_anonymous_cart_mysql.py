import hashlib
import pytest
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from carts.services.resolver import hash_cart_token
from carts.models import Cart, CartItem
from products.models import Product


CART_TOKEN_COOKIE = "cart_token"
CART_TOKEN_HEADER = "X-Cart-Token"


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def http_header(name: str) -> str:
    return f"HTTP_{name.replace('-', '_').upper()}"


def extract_cookie_token(response) -> str:
    assert CART_TOKEN_COOKIE in response.cookies, f"Missing cookie {CART_TOKEN_COOKIE}"
    return response.cookies[CART_TOKEN_COOKIE].value


def login(client: APIClient, email: str, password: str, cart_token: str | None = None):
    kwargs = {}
    if cart_token:
        kwargs[http_header(CART_TOKEN_HEADER)] = cart_token
    res = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
        **kwargs,
    )
    return res


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_db_unique_constraint_on_anonymous_token_hash():
    """
    MySQL: ensure anonymous_token_hash is UNIQUE and enforced.
    This catches migration/DB config issues that SQLite may not model equivalently.
    """
    # This assumes Cart has field anonymous_token_hash (nullable)
    token_hash = sha256_hex("fixed_token_value")

    # ORM save() runs full_clean(), which raises ValidationError before DB insert.
    Cart.objects.create(status=Cart.Status.ACTIVE,
                        anonymous_token_hash=token_hash)
    with pytest.raises(ValidationError):
        Cart.objects.create(status=Cart.Status.ACTIVE,
                            anonymous_token_hash=token_hash)

    # DB-level assertion: bypass model validation via bulk_create (no full_clean()).
    with pytest.raises(IntegrityError):
        Cart.objects.bulk_create([
            Cart(status=Cart.Status.ACTIVE, anonymous_token_hash="bulk_h1"),
            Cart(status=Cart.Status.ACTIVE, anonymous_token_hash="bulk_h1"),
        ])


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_get_or_create_anonymous_cart_is_idempotent_for_same_token_hash(product):
    """
    Regression: given the same token multiple times, we should not create multiple carts.
    This is often impacted by MySQL constraints and transaction boundaries.
    """
    client = APIClient()

    # first call creates guest cart and sets token cookie
    add = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    assert add.status_code == 201, add.content
    token = extract_cookie_token(add)

    # simulate "same token, no cookie jar" using header
    c2 = APIClient()
    res1 = c2.get("/api/v1/cart/", **{http_header(CART_TOKEN_HEADER): token})
    res2 = c2.get("/api/v1/cart/", **{http_header(CART_TOKEN_HEADER): token})

    assert res1.status_code in (200, 201), res1.content
    assert res2.status_code in (200, 201), res2.content
    assert res1.json()["id"] == res2.json()["id"]

    # DB should contain exactly one ACTIVE anonymous cart for that token hash
    token_hash = sha256_hex(token)
    assert Cart.objects.filter(
        status=Cart.Status.ACTIVE, anonymous_token_hash=token_hash).count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_login_merge_is_idempotent_token_reuse_does_not_duplicate_items():
    """
    MySQL-focused idempotency:
    If the same guest token is used again after a successful login merge/adopt,
    it must not merge again and must not duplicate quantities.
    """
    # Product with enough stock
    p = Product.objects.create(
        name="E2E_IDEMP", price=10, stock_quantity=100, is_active=True)

    User = get_user_model()
    user = User.objects.create_user(
        email="idem@example.com", password="Passw0rd!123")

    # user cart already has 2
    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(cart=user_cart, product=p,
                            quantity=2, price_at_add_time=p.price)

    # guest cart adds 3
    guest = APIClient()
    add = guest.post("/api/v1/cart/items/",
                     {"product_id": p.id, "quantity": 3}, format="json")
    assert add.status_code == 201, add.content
    token = extract_cookie_token(add)

    # first login -> merge should happen: 2 + 3 = 5
    res1 = login(guest, user.email, "Passw0rd!123", cart_token=token)
    assert res1.status_code == 200, res1.content

    # check user cart quantity is 5
    item = CartItem.objects.get(cart=user_cart, product=p)
    assert item.quantity == 5

    # second login attempt reusing the same token must NOT change quantity
    guest2 = APIClient()
    res2 = login(guest2, user.email, "Passw0rd!123", cart_token=token)
    # acceptable behaviours:
    # - 200 with no merge applied (idempotent no-op)
    # - 401/404 because token is invalid
    assert res2.status_code in (200, 401, 404), res2.content

    item.refresh_from_db()
    assert item.quantity == 5


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_converted_cart_is_not_merge_target_on_login(product):
    """
    MySQL suite: ensure merge/adopt targets ONLY ACTIVE cart.
    If user has only CONVERTED carts, login should adopt guest cart into new ACTIVE cart
    (or create new ACTIVE then merge) but must not merge into CONVERTED.
    """
    User = get_user_model()
    user = User.objects.create_user(
        email="converted@example.com", password="Passw0rd!123")

    # user has only CONVERTED cart
    converted = Cart.objects.create(user=user, status=Cart.Status.CONVERTED)

    # guest has an item
    guest = APIClient()
    add = guest.post("/api/v1/cart/items/",
                     {"product_id": product.id, "quantity": 2}, format="json")
    assert add.status_code == 201, add.content
    token = extract_cookie_token(add)

    res = login(guest, user.email, "Passw0rd!123", cart_token=token)
    assert res.status_code == 200, res.content

    # there should now be an ACTIVE cart for user
    active = Cart.objects.get(user=user, status=Cart.Status.ACTIVE)
    assert active.id != converted.id

    # and it should contain the guest item
    item = CartItem.objects.get(cart=active, product=product)
    assert item.quantity == 2


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_integrity_error_on_token_hash_collision_is_handled_as_safe_retry(product, monkeypatch):
    """
    This is a deterministic stand-in for a race:
    Simulate a collision / duplicate token_hash insert.
    The service should catch IntegrityError and retry token generation (or map to safe behaviour),
    never returning 500.

    Implementation expectation:
    - on create anonymous cart, if token_hash unique constraint fails, regenerate token and retry
    """
    # Precreate a cart with hash(AAAA) to force collision on first attempt
    Cart.objects.create(
        user=None,
        status=Cart.Status.ACTIVE,
        anonymous_token_hash=hash_cart_token("AAAA"),
    )

    # Force token generator: first returns "AAAA" (collision), then "BBBB" (success)
    tokens = iter(["AAAA", "BBBB"])

    def fake_generate():
        return next(tokens)

    # Patch the generator in the module where it's imported/used
    monkeypatch.setattr(
        "api.views.carts.generate_cart_token", fake_generate)

    client = APIClient()
    res = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    assert res.status_code == 201, res.content

    # Ensure cookie token is set to the second (non-colliding) value
    assert "cart_token" in res.cookies
    assert res.cookies["cart_token"].value == "BBBB"


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_two_logins_with_same_token_only_one_can_merge_if_processed_twice():
    """
    Another race-oriented deterministic test:
    token should be invalidated atomically such that once merged, it cannot be merged again.
    We'll simulate by:
    - creating user cart and guest cart
    - calling login twice sequentially with same token
    - ensure only first changes quantities
    """
    p = Product.objects.create(
        name="E2E_RACE", price=10, stock_quantity=100, is_active=True)
    User = get_user_model()
    user = User.objects.create_user(
        email="race@example.com", password="Passw0rd!123")

    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    CartItem.objects.create(cart=user_cart, product=p,
                            quantity=1, price_at_add_time=p.price)

    guest = APIClient()
    add = guest.post("/api/v1/cart/items/",
                     {"product_id": p.id, "quantity": 2}, format="json")
    assert add.status_code == 201, add.content
    token = extract_cookie_token(add)

    r1 = login(APIClient(), user.email, "Passw0rd!123", cart_token=token)
    assert r1.status_code == 200, r1.content
    CartItem.objects.get(cart=user_cart, product=p).refresh_from_db()
    assert CartItem.objects.get(cart=user_cart, product=p).quantity == 3

    r2 = login(APIClient(), user.email, "Passw0rd!123", cart_token=token)
    assert r2.status_code in (200, 401, 404), r2.content
    assert CartItem.objects.get(cart=user_cart, product=p).quantity == 3
