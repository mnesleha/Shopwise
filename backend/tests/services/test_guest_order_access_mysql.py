import pytest

from orders.models import Order
from tests.conftest import create_valid_order

from orders.services.guest_order_access_service import GuestOrderAccessService

pytestmark = pytest.mark.mysql


@pytest.mark.django_db(transaction=True)
def test_guest_token_hash_persists_mysql():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    token = GuestOrderAccessService.issue_token(order=order)
    assert token

    order.refresh_from_db()
    assert order.guest_access_token_hash is not None
