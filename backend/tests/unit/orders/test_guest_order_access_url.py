import pytest
from urllib.parse import urlparse, parse_qs

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
    parsed = urlparse(url)
    assert parsed.scheme == "http"
    assert parsed.netloc == "127.0.0.1:8000"
    assert parsed.path == f"/guest/orders/{order.id}/"
    assert parse_qs(parsed.query)["token"] == [token]
