import pytest
from rest_framework.test import APIClient
from products.models import Product


def _extract_cart_token_cookie(resp) -> str:
    # Align with anonymous cart tests: cookie name may differ; adjust if needed.
    return resp.cookies.get("cart_token").value


@pytest.mark.django_db
def test_put_cart_item_creates_item_returns_201_and_cart_snapshot(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    # ensure cart exists
    auth_client.get("/api/v1/cart/")

    resp = auth_client.put(
        f"/api/v1/cart/items/{product.id}/",
        {"quantity": 2},
        format="json",
    )

    assert resp.status_code == 201
    body = resp.json()

    # cart snapshot shape expectations (keep minimal)
    assert "items" in body
    assert any(i["product"]["id"] == product.id and i["quantity"]
               == 2 for i in body["items"])


@pytest.mark.django_db
def test_put_cart_item_updates_existing_item_returns_200_and_cart_snapshot(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    auth_client.get("/api/v1/cart/")
    # create via legacy POST (existing behavior)
    r1 = auth_client.post(
        "/api/v1/cart/items/", {"product_id": product.id, "quantity": 1}, format="json")
    assert r1.status_code in (200, 201)

    resp = auth_client.put(
        f"/api/v1/cart/items/{product.id}/",
        {"quantity": 3},
        format="json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert any(i["product"]["id"] == product.id and i["quantity"]
               == 3 for i in body["items"])


@pytest.mark.django_db
def test_put_cart_item_quantity_zero_removes_item_returns_200_cart_snapshot(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    auth_client.get("/api/v1/cart/")
    auth_client.post("/api/v1/cart/items/",
                     {"product_id": product.id, "quantity": 2}, format="json")

    resp = auth_client.put(
        f"/api/v1/cart/items/{product.id}/",
        {"quantity": 0},
        format="json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert all(i["product"]["id"] != product.id for i in body["items"])


@pytest.mark.django_db
def test_put_cart_item_quantity_negative_returns_400(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    auth_client.get("/api/v1/cart/")
    resp = auth_client.put(
        f"/api/v1/cart/items/{product.id}/",
        {"quantity": -1},
        format="json",
    )

    assert resp.status_code == 400
    assert resp.json().get("code") in ("VALIDATION_ERROR",
                                       "VALIDATION_ERROR_INVALID_INPUT", "VALIDATION_ERROR_BODY")


@pytest.mark.django_db
def test_put_cart_item_quantity_missing_returns_400(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    auth_client.get("/api/v1/cart/")
    resp = auth_client.put(
        f"/api/v1/cart/items/{product.id}/",
        {},
        format="json",
    )

    assert resp.status_code == 400


@pytest.mark.django_db
def test_put_cart_item_out_of_stock_returns_409(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=1, is_active=True)

    auth_client.get("/api/v1/cart/")
    resp = auth_client.put(
        f"/api/v1/cart/items/{product.id}/",
        {"quantity": 2},
        format="json",
    )

    assert resp.status_code == 409
    assert resp.json().get("code") == "OUT_OF_STOCK"


@pytest.mark.django_db
def test_delete_cart_item_removes_item_returns_200_cart_snapshot(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    auth_client.get("/api/v1/cart/")
    auth_client.post("/api/v1/cart/items/",
                     {"product_id": product.id, "quantity": 2}, format="json")

    resp = auth_client.delete(
        f"/api/v1/cart/items/{product.id}/",
        format="json",
    )

    assert resp.status_code == 200
    body = resp.json()
    assert all(i["product"]["id"] != product.id for i in body["items"])


@pytest.mark.django_db
def test_delete_cart_item_is_idempotent_returns_200(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    auth_client.get("/api/v1/cart/")
    # delete even if not present
    resp = auth_client.delete(
        f"/api/v1/cart/items/{product.id}/", format="json")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.django_db
def test_guest_put_creates_sets_cookie_and_updates_and_delete_works():
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)
    client = APIClient()

    r1 = client.put(
        f"/api/v1/cart/items/{product.id}/", {"quantity": 2}, format="json")
    assert r1.status_code == 201
    assert "items" in r1.json()

    token = _extract_cart_token_cookie(r1)
    assert token

    # update via same client (cookie persists)
    r2 = client.put(
        f"/api/v1/cart/items/{product.id}/", {"quantity": 3}, format="json")
    assert r2.status_code == 200
    assert any(i["product"]["id"] == product.id and i["quantity"]
               == 3 for i in r2.json()["items"])

    # delete
    r3 = client.delete(f"/api/v1/cart/items/{product.id}/", format="json")
    assert r3.status_code == 200
    assert all(i["product"]["id"] != product.id for i in r3.json()["items"])


@pytest.mark.django_db
def test_guest_can_use_cart_token_header_for_put_and_delete():
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=True)

    c1 = APIClient()
    r1 = c1.put(f"/api/v1/cart/items/{product.id}/",
                {"quantity": 2}, format="json")
    assert r1.status_code == 201
    token = _extract_cart_token_cookie(r1)
    assert token

    # new client without cookies, uses header token
    c2 = APIClient()
    c2.credentials(HTTP_X_CART_TOKEN=token)

    r2 = c2.put(f"/api/v1/cart/items/{product.id}/",
                {"quantity": 4}, format="json")
    assert r2.status_code == 200
    assert any(i["product"]["id"] == product.id and i["quantity"]
               == 4 for i in r2.json()["items"])

    r3 = c2.delete(f"/api/v1/cart/items/{product.id}/", format="json")
    assert r3.status_code == 200
    assert all(i["product"]["id"] != product.id for i in r3.json()["items"])


@pytest.mark.django_db
def test_put_inactive_product_returns_error(auth_client):
    product = Product.objects.create(
        name="P", price=10, stock_quantity=10, is_active=False)
    auth_client.get("/api/v1/cart/")

    resp = auth_client.put(
        f"/api/v1/cart/items/{product.id}/", {"quantity": 1}, format="json")
    assert resp.status_code in (404, 409)
    assert resp.json().get("code") == "PRODUCT_UNAVAILABLE"
