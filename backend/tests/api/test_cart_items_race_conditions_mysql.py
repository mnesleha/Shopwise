import pytest
import threading
import traceback
from typing import Callable, Any
from rest_framework.test import APIClient
from products.models import Product
from carts.models import ActiveCart, Cart, CartItem
from carts.services.active_cart_service import get_or_create_active_cart_for_user


def _client_for_user(user) -> APIClient:
    """
    Create a fresh DRF APIClient authenticated via force_authenticate.
    This avoids relying on the login/JWT endpoint for concurrency tests.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _run_concurrently(fn1: Callable[[], Any], fn2: Callable[[], Any]) -> tuple[Any, Any]:
    """
    Run two callables concurrently, aligned via a barrier, and return their results.
    If either thread raises, re-raise the exception in the main thread.
    """
    barrier = threading.Barrier(2)
    out = [None, None]
    err = [None, None]

    def wrap(i: int, fn: Callable[[], Any]):
        try:
            barrier.wait()
            out[i] = fn()
        except Exception as e:
            err[i] = RuntimeError(
                f"Thread {i} raised {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )

    t1 = threading.Thread(target=wrap, args=(0, fn1))
    t2 = threading.Thread(target=wrap, args=(1, fn2))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    if err[0]:
        raise err[0]
    if err[1]:
        raise err[1]
    return out[0], out[1]


@pytest.mark.mysql(transaction=True)
@pytest.mark.django_db(transaction=True)
def test_mysql_race_put_same_item_last_write_wins_no_duplicates(user, forced_auth_client):
    """
    Two concurrent PUTs to the same cart item should not create duplicates.
    Final quantity can be either value depending on timing (last-write-wins),
    but there must be exactly one cart item row for the product.
    """
    product = Product.objects.create(
        name="P", price=10, stock_quantity=100, is_active=True)

    c1 = forced_auth_client
    c2 = _client_for_user(user)

    c1.get("/api/v1/cart/")
    c2.get("/api/v1/cart/")

    def put_qty_2():
        return c1.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 2}, format="json")

    def put_qty_5():
        return c2.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 5}, format="json")

    r1, r2 = _run_concurrently(put_qty_2, put_qty_5)

    assert r1.status_code in (200, 201), r1.content
    assert r2.status_code in (200, 201), r2.content

    final = c1.get("/api/v1/cart/")
    assert final.status_code == 200
    items = final.json()["items"]

    matches = [i for i in items if i["product"]["id"] == product.id]
    assert len(matches) == 1
    assert matches[0]["quantity"] in (2, 5)


@pytest.mark.mysql(transaction=True)
@pytest.mark.django_db(transaction=True)
def test_mysql_race_put_create_same_item_no_unique_violation(user, forced_auth_client):
    """
    Two concurrent PUTs that both attempt to 'create' the same item must not
    violate unique constraints and must result in exactly one item row.
    """
    product = Product.objects.create(
        name="P", price=10, stock_quantity=100, is_active=True)

    # IMPORTANT:
    # APIClient is not thread-safe. Do NOT share a client (or forced_auth_client fixture)
    # across concurrent threads. Each thread gets its own authenticated client.
    def put_qty_1():
        c = _client_for_user(user)
        me = c.get("/api/v1/auth/me/")
        assert me.status_code == 200, me.content
        c.get("/api/v1/cart/")
        return c.put(
            f"/api/v1/cart/items/{product.id}/",
            {"quantity": 1},
            format="json",
        )

    def put_qty_1_again():
        c = _client_for_user(user)
        me = c.get("/api/v1/auth/me/")
        assert me.status_code == 200, me.content
        c.get("/api/v1/cart/")
        return c.put(
            f"/api/v1/cart/items/{product.id}/",
            {"quantity": 1},
            format="json",
        )

    r1, r2 = _run_concurrently(put_qty_1, put_qty_1_again)

    assert r1.status_code in (200, 201), r1.content
    assert r2.status_code in (200, 201), r2.content

    # Use a fresh authenticated client for verification
    verifier = _client_for_user(user)
    final = verifier.get("/api/v1/cart/").json()["items"]
    matches = [i for i in final if i["product"]["id"] == product.id]
    assert len(matches) == 1
    assert matches[0]["quantity"] == 1

    # Strong DB-level assertion: never more than one row per (cart, product) in ACTIVE cart
    cart, _ = get_or_create_active_cart_for_user(user)
    assert CartItem.objects.filter(
        cart=cart, product_id=product.id).count() == 1


@pytest.mark.mysql(transaction=True)
@pytest.mark.django_db(transaction=True)
def test_mysql_race_delete_vs_put_results_in_consistent_state(user, forced_auth_client):
    """
    Concurrent DELETE and PUT on the same item must end in a consistent state:
    - either the item is removed (DELETE wins),
    - or the item exists with the PUT quantity (PUT wins).
    No duplicates allowed.
    """
    product = Product.objects.create(
        name="P", price=10, stock_quantity=100, is_active=True)

    c1 = forced_auth_client
    c2 = _client_for_user(user)

    c1.get("/api/v1/cart/")
    c2.get("/api/v1/cart/")

    # create initial item
    c1.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 2}, format="json")

    def do_delete():
        return c1.delete(f"/api/v1/cart/items/{product.id}/", format="json")

    def do_put_3():
        return c2.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 3}, format="json")

    r_del, r_put = _run_concurrently(do_delete, do_put_3)

    assert r_del.status_code == 200, r_del.content
    assert r_put.status_code in (200, 201), r_put.content

    final_items = c1.get("/api/v1/cart/").json()["items"]
    matches = [i for i in final_items if i["product"]["id"] == product.id]

    assert len(matches) in (0, 1)
    if matches:
        assert matches[0]["quantity"] == 3


@pytest.mark.mysql(transaction=True)
@pytest.mark.django_db(transaction=True)
def test_mysql_race_put_zero_vs_put_positive_consistent_state(user, forced_auth_client):
    """
    PUT quantity=0 acts as remove (DELETE alias). Concurrent remove and PUT>0
    must end in a consistent state: removed OR single item with PUT quantity.
    """
    product = Product.objects.create(
        name="P", price=10, stock_quantity=100, is_active=True)

    c1 = forced_auth_client
    c2 = _client_for_user(user)

    c1.get("/api/v1/cart/")
    c2.get("/api/v1/cart/")

    c1.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 2}, format="json")

    def put_zero():
        return c1.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 0}, format="json")

    def put_four():
        return c2.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 4}, format="json")

    r1, r2 = _run_concurrently(put_zero, put_four)

    assert r1.status_code == 200, r1.content
    assert r2.status_code in (200, 201), r2.content

    final_items = c1.get("/api/v1/cart/").json()["items"]
    matches = [i for i in final_items if i["product"]["id"] == product.id]

    assert len(matches) in (0, 1)
    if matches:
        assert matches[0]["quantity"] == 4


@pytest.mark.mysql(transaction=True)
@pytest.mark.django_db(transaction=True)
def test_mysql_race_out_of_stock_puts_do_not_create_item(user, forced_auth_client):
    """
    Concurrent PUTs requesting quantity above stock must not create the item.
    Both requests should return 409 OUT_OF_STOCK.
    """
    product = Product.objects.create(
        name="P", price=10, stock_quantity=1, is_active=True)

    c1 = forced_auth_client
    c2 = _client_for_user(user)

    c1.get("/api/v1/cart/")
    c2.get("/api/v1/cart/")

    def put_qty_2_a():
        return c1.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 2}, format="json")

    def put_qty_2_b():
        return c2.put(f"/api/v1/cart/items/{product.id}/", {"quantity": 2}, format="json")

    r1, r2 = _run_concurrently(put_qty_2_a, put_qty_2_b)

    assert r1.status_code == 409, r1.content
    assert r2.status_code == 409, r2.content
    assert r1.json().get("code") == "OUT_OF_STOCK"
    assert r2.json().get("code") == "OUT_OF_STOCK"

    final_items = c1.get("/api/v1/cart/").json()["items"]
    assert all(i["product"]["id"] != product.id for i in final_items)


@pytest.mark.mysql(transaction=True)
@pytest.mark.django_db(transaction=True)
def test_mysql_race_get_cart_creates_single_active_cart(user):
    c1 = _client_for_user(user)
    c2 = _client_for_user(user)

    def get1():
        return c1.get("/api/v1/cart/")

    def get2():
        return c2.get("/api/v1/cart/")

    r1, r2 = _run_concurrently(get1, get2)

    assert r1.status_code == 200, r1.content
    assert r2.status_code == 200, r2.content

    assert ActiveCart.objects.filter(user=user).count() == 1
    assert Cart.objects.filter(
        user=user, status=Cart.Status.ACTIVE).count() == 1
