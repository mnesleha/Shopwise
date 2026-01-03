import re
import pytest

from orders.models import Order


UPPER_SNAKE = re.compile(r"^[A-Z0-9_]+$")


def assert_error_payload(data: dict):
    assert isinstance(data, dict)
    assert "code" in data
    assert "message" in data
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str)
    assert UPPER_SNAKE.match(
        data["code"]), f"code is not UPPER_SNAKE_CASE: {data['code']}"


@pytest.mark.django_db
def test_error_codes_are_uppercase_for_validation_error(auth_client, user, order_factory):
    """
    400 should be VALIDATION_ERROR (serializer validation) and include errors.
    """
    order = order_factory(user=user, status=Order.Status.CREATED)

    r = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "maybe"},  # invalid choice
        format="json",
    )

    assert r.status_code == 400
    data = r.json()

    assert_error_payload(data)
    assert data["code"] == "VALIDATION_ERROR"
    assert "errors" in data
    assert isinstance(data["errors"], dict)


@pytest.mark.django_db
def test_error_codes_are_uppercase_for_not_found(auth_client, user):
    """
    404 should return {code,message} with uppercase code.
    Use payments order lookup (non-existent order_id).
    """
    r = auth_client.post(
        "/api/v1/payments/",
        {"order_id": 999999, "result": "success"},
        format="json",
    )

    assert r.status_code == 404
    data = r.json()
    assert_error_payload(data)
    assert data["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_error_codes_are_uppercase_for_conflict(auth_client, user, order_factory):
    """
    409 should return {code,message} with uppercase code.
    Use payments double-submit to force conflict.
    """
    order = order_factory(user=user, status=Order.Status.CREATED)

    payload = {"order_id": order.id, "result": "success"}
    r1 = auth_client.post("/api/v1/payments/", payload, format="json")
    r2 = auth_client.post("/api/v1/payments/", payload, format="json")

    assert r1.status_code == 201
    assert r2.status_code == 409

    data = r2.json()
    assert_error_payload(data)

    # Ensure it's a conflict-type code, but allow business-specific values.
    assert data["code"] != "VALIDATION_ERROR"
