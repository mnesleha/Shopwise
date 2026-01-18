import pytest

from orders.models import Order
from tests.conftest import create_valid_order

from orders.services.guest_order_access_service import generate_guest_access_url


pytestmark = pytest.mark.django_db


def test_generate_guest_access_url_contains_order_id_and_token(settings):
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    token = "tok_123"
    settings.PUBLIC_BASE_URL = "http://127.0.0.1:8000"

    url = generate_guest_access_url(order=order, token=token)
    assert str(order.id) in url
    assert "token=tok_123" in url
    assert url.startswith("http://127.0.0.1:8000")
