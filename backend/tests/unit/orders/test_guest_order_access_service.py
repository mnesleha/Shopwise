import pytest

from django.utils import timezone

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


def test_issue_token_raises_for_non_guest_order(user):
    order = create_valid_order(
        user=user, status=Order.Status.CREATED, customer_email=user.email)
    with pytest.raises(ValueError):
        GuestOrderAccessService.issue_token(order=order)


def test_validate_returns_none_for_empty_token():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    GuestOrderAccessService.issue_token(order=order)

    assert GuestOrderAccessService.validate(
        order_id=order.id, token="") is None
    assert GuestOrderAccessService.validate(
        order_id=order.id, token=None) is None


def test_validate_returns_none_when_no_hash_stored():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")
    # no token issued -> hash is None
    assert GuestOrderAccessService.validate(
        order_id=order.id, token="anything") is None


def test_validate_returns_none_for_nonexistent_order_id():
    assert GuestOrderAccessService.validate(
        order_id=999999999, token="anything") is None
