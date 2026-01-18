import pytest

from orders.models import Order
from tests.conftest import create_valid_order

from orders.services.guest_order_access_service import GuestOrderAccessService

pytestmark = pytest.mark.django_db


def test_issue_token_stores_only_hash_not_plaintext():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    token = GuestOrderAccessService.issue_token(order=order)
    assert isinstance(token, str)
    assert len(token) >= 20

    order.refresh_from_db()
    assert order.guest_access_token_hash is not None
    assert token != order.guest_access_token_hash


def test_validate_token_returns_order_for_valid_token():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    token = GuestOrderAccessService.issue_token(order=order)
    got = GuestOrderAccessService.validate(order_id=order.id, token=token)

    assert got is not None
    assert got.id == order.id


def test_validate_token_returns_none_for_invalid_token():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    GuestOrderAccessService.issue_token(order=order)
    got = GuestOrderAccessService.validate(
        order_id=order.id, token="invalid-token")

    assert got is None
