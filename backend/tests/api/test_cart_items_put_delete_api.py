import pytest
from products.models import Product


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
