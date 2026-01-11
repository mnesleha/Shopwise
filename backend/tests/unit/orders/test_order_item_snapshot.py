import pytest
from products.models import Product
from orderitems.models import OrderItem
from tests.conftest import checkout_payload


@pytest.mark.django_db
def test_order_item_persists_price_snapshot_after_checkout(auth_client, user):
    product = Product.objects.create(
        name="Snapshot product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    auth_client.get("/api/v1/cart/")

    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )

    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    print(resp.status_code, resp.json())

    assert resp.status_code == 201

    item = OrderItem.objects.first()
    assert item is not None

    # These fields will be introduced in PR1 (model) and filled in PR2 (checkout persistence)
    assert item.unit_price_at_order_time is not None
    assert item.line_total_at_order_time is not None
