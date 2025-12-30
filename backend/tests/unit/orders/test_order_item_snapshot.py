import pytest
from orderitems.models import OrderItem


@pytest.mark.django_db
def test_order_item_persists_price_snapshot_after_checkout(auth_client, user):
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": 6, "quantity": 2},
        format="json",
    )
    auth_client.post("/api/v1/cart/checkout/")

    item = OrderItem.objects.first()

    assert item.unit_price_at_order_time is not None
    assert item.line_total_at_order_time is not None
    assert item.unit_price_at_order_time >= 0
    assert item.line_total_at_order_time >= 0
