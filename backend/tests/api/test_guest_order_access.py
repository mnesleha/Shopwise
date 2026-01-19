import pytest

from orders.models import Order
from tests.conftest import create_valid_order

from orders.services.guest_order_access_service import GuestOrderAccessService


pytestmark = pytest.mark.django_db


def test_guest_order_access_valid_token_returns_200(client):
    # guest order (user=None)
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    # issue token via service (implemented in PR)

    token = GuestOrderAccessService.issue_token(order=order)

    resp = client.get(f"/api/v1/guest/orders/{order.id}/", {"token": token})
    assert resp.status_code == 200, resp.content
    assert resp.json()["id"] == order.id


def test_guest_order_access_invalid_token_returns_404(client):
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    resp = client.get(
        f"/api/v1/guest/orders/{order.id}/", {"token": "invalid-token"})
    assert resp.status_code == 404


def test_guest_order_access_missing_token_returns_404(client):
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    resp = client.get(f"/api/v1/guest/orders/{order.id}/")
    assert resp.status_code == 404


def test_guest_order_access_non_guest_order_returns_404(auth_client, user):
    # authenticated order (not guest)
    order = create_valid_order(
        user=user, status=Order.Status.CREATED, customer_email=user.email)

    # Even if token provided, must not allow access
    resp = auth_client.get(
        f"/api/v1/guest/orders/{order.id}/", {"token": "anything"})
    assert resp.status_code == 404


def test_guest_order_access_wrong_order_id_returns_404(client):
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    token = GuestOrderAccessService.issue_token(order=order)

    # order_id does not exist (or at least not this one)
    resp = client.get(
        f"/api/v1/guest/orders/{order.id + 99999}/", {"token": token})
    assert resp.status_code == 404
