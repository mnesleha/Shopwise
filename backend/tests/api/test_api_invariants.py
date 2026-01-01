import re
import pytest

UPPER_SNAKE_CASE = re.compile(r"^[A-Z][A-Z0-9_]*$")
MONEY_2DP = re.compile(r"^\d+\.\d{2}$")


@pytest.mark.django_db
def test_error_response_code_is_uppercase_snake_case(auth_client):
    """
    Contract guard:
    All API error responses must use UPPER_SNAKE_CASE error codes.
    """
    # Trigger a known error deterministically: checkout with no active cart
    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 404

    payload = response.json()
    assert "code" in payload
    assert isinstance(payload["code"], str)
    assert UPPER_SNAKE_CASE.match(payload["code"]), payload["code"]


@pytest.mark.django_db
def test_checkout_success_response_uses_unified_contract(auth_client, product):
    """
    Contract guard:
    Checkout response must follow the unified order contract.
    """
    # Arrange: add one item to cart
    r = auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    assert r.status_code in (200, 201)

    # Act: checkout
    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 201
    data = response.json()

    # Top-level contract
    assert set(data.keys()) == {"id", "status", "items", "total"}
    assert isinstance(data["id"], int)
    assert isinstance(data["status"], str)
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], str)
    assert MONEY_2DP.match(data["total"]), data["total"]

    # Item contract (at least one)
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert set(item.keys()) == {
        "id",
        "product",
        "quantity",
        "unit_price",
        "line_total",
        "discount",
    }

    assert isinstance(item["id"], int)
    assert item["id"] > 0
    assert isinstance(item["product"], int)
    assert isinstance(item["quantity"], int)
    assert isinstance(item["unit_price"], str)
    assert isinstance(item["line_total"], str)
    assert MONEY_2DP.match(item["unit_price"]), item["unit_price"]
    assert MONEY_2DP.match(item["line_total"]), item["line_total"]

    # discount object or null
    if item["discount"] is None:
        assert item["discount"] is None
    else:
        assert set(item["discount"].keys()) == {"type", "value"}
        assert item["discount"]["type"] in {"FIXED", "PERCENT"}
        assert isinstance(item["discount"]["value"], str)
        assert MONEY_2DP.match(
            item["discount"]["value"]), item["discount"]["value"]


@pytest.mark.django_db
def test_money_fields_are_strings_with_two_decimals(auth_client, product):
    """
    Contract guard:
    Monetary fields exposed by the API are strings with exactly 2 decimals.
    """
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )
    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 201
    data = response.json()

    assert MONEY_2DP.match(data["total"])
    for item in data["items"]:
        assert MONEY_2DP.match(item["unit_price"])
        assert MONEY_2DP.match(item["line_total"])
        if item["discount"] is not None:
            assert MONEY_2DP.match(item["discount"]["value"])


@pytest.mark.django_db
def test_error_payload_has_code_and_message_or_detail(auth_client):
    """
    Contract guard:
    Error responses must include a stable error 'code' and human-readable text
    in 'message' (preferred) or 'detail' (legacy/DRF default).
    """
    response = auth_client.post("/api/v1/cart/checkout/")
    assert response.status_code == 404

    payload = response.json()

    assert "code" in payload
    assert isinstance(payload["code"], str)
    assert UPPER_SNAKE_CASE.match(payload["code"]), payload["code"]

    assert ("message" in payload) or ("detail" in payload), payload
    if "message" in payload:
        assert isinstance(payload["message"], str)
        assert payload["message"].strip() != ""
    if "detail" in payload:
        assert isinstance(payload["detail"], str)
        assert payload["detail"].strip() != ""


@pytest.mark.django_db
def test_double_payment_submit_returns_409(auth_client, user, order_factory):
    """
    Contract guard:
    A second payment attempt for the same order must return 409 Conflict
    (not 404, because the order exists but is not payable / already processed).
    """
    order = order_factory(user=user)

    payload = {"order_id": order.id, "result": "success"}

    r1 = auth_client.post("/api/v1/payments/", payload, format="json")
    assert r1.status_code == 201, r1.content

    r2 = auth_client.post("/api/v1/payments/", payload, format="json")
    assert r2.status_code == 409, r2.content

    data = r2.json()
    assert "code" in data
    assert UPPER_SNAKE_CASE.match(data["code"]), data["code"]
