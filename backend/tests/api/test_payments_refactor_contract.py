import pytest

from payments.models import Payment
from orders.models import Order
from tests.conftest import create_valid_order  # uses full required payload


pytestmark = pytest.mark.django_db


def test_payments_create_success_keeps_contract(auth_client, user):
    order = create_valid_order(user=user, status=Order.Status.CREATED)

    resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "success"},
        format="json",
    )

    assert resp.status_code == 201, resp.content
    assert resp.data["order"] == order.id
    assert resp.data["status"] == Payment.Status.SUCCESS

    order.refresh_from_db()
    assert order.status == Order.Status.PAID


def test_payments_create_fail_keeps_contract(auth_client, user):
    order = create_valid_order(user=user, status=Order.Status.CREATED)

    resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "fail"},
        format="json",
    )

    assert resp.status_code == 201, resp.content
    assert resp.data["order"] == order.id
    assert resp.data["status"] == Payment.Status.FAILED

    order.refresh_from_db()
    assert order.status == Order.Status.PAYMENT_FAILED


def test_payments_create_returns_409_if_not_payable(auth_client, user):
    order = create_valid_order(user=user, status=Order.Status.PAID)

    resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "success"},
        format="json",
    )

    assert resp.status_code == 409, resp.content
    assert resp.data["code"] == "ORDER_NOT_PAYABLE"


def test_payments_create_returns_409_if_payment_exists(auth_client, user):
    order = create_valid_order(user=user, status=Order.Status.CREATED)
    Payment.objects.create(order=order, status=Payment.Status.SUCCESS)

    resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "success"},
        format="json",
    )

    assert resp.status_code == 409, resp.content
    assert resp.data["code"] == "PAYMENT_ALREADY_EXISTS"


def test_payments_create_returns_404_for_other_users_order(auth_client, django_user_model):
    other = django_user_model.objects.create_user(
        email="other@example.com",
        password="Passw0rd!123",
        first_name="Other",
        last_name="User",
    )
    order = create_valid_order(user=other, status=Order.Status.CREATED)

    resp = auth_client.post(
        "/api/v1/payments/",
        {"order_id": order.id, "result": "success"},
        format="json",
    )

    assert resp.status_code == 404, resp.content
    assert resp.data["code"] == "NOT_FOUND"
