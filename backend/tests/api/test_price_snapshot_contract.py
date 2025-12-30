import pytest
from products.models import Product


@pytest.mark.django_db
def test_checkout_returns_unit_price_and_line_total(auth_client, user, fixed_discount):
    """
    Frontend contract test:
    item must expose unit_price and line_total explicitly.
    """
    product = Product.objects.create(
        name="Test product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    fixed_discount(product=product, value="150.00")

    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/")
    data = response.json()

    item = data["items"][0]

    assert item["unit_price"] == "100.00"
    assert item["quantity"] == 2
    assert item["line_total"] == "0.00"
    assert data["total"] == "0.00"
