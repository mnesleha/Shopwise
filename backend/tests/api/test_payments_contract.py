import re
import pytest

from orders.models import Order


PAYMENT_OK_KEYS = {"id", "status", "order"}
ERROR_KEYS = {"code", "message"}


@pytest.mark.django_db
def test_payments_create_returns_contract_shape(auth_client, user, order_factory):
    """
    Contract:
    201 returns payment object: {id:int, status:str, order:int}
    """
    order = order_factory(user=user)

    r = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "success"},
        format="json",
    )

    assert r.status_code == 201
    data = r.json()

    assert set(data.keys()) == PAYMENT_OK_KEYS
    assert isinstance(data["id"], int)
    assert isinstance(data["status"], str)
    assert data["status"] == "SUCCESS"  # Validate actual value, not just type
    assert isinstance(data["order"], int)
    assert data["order"] == order.id


@pytest.mark.django_db
def test_payments_invalid_result_returns_400_error_shape(auth_client, user, order_factory):
    """
    Contract:
    400 returns {code, message} and code is UPPER_SNAKE_CASE.
    """
    order = order_factory(user=user)

    r = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "maybe"},
        format="json",
    )

    assert r.status_code == 400
    data = r.json()

    assert set(data.keys()) >= ERROR_KEYS
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str)
    assert re.match(r"^[A-Z][A-Z0-9_]*$", data["code"])


@pytest.mark.django_db
def test_payments_order_not_found_returns_404_error_shape(auth_client, user):
    """
    Contract:
    404 returns {code, message} (not DRF {detail}).
    """
    r = auth_client.post(
        "/api/v1/payments/",
        {"order_id": 999999, "result": "success"},
        format="json",
    )

    assert r.status_code == 404
    data = r.json()
    assert set(data.keys()) >= ERROR_KEYS
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str)


@pytest.mark.django_db
def test_payments_double_submit_returns_409_error_shape(auth_client, user, order_factory):
    """
    Business rule:
    Each order can have only one payment. Second submit => 409.
    """
    order = order_factory(user=user)

    payload = {"order_id": order.id, "result": "success"}
    r1 = auth_client.post("/api/v1/payments/", payload, format="json")
    r2 = auth_client.post("/api/v1/payments/", payload, format="json")

    assert r1.status_code == 201
    assert r2.status_code == 409

    data = r2.json()
    assert set(data.keys()) >= ERROR_KEYS
    assert re.match(r"^[A-Z][A-Z0-9_]*$", data["code"])
