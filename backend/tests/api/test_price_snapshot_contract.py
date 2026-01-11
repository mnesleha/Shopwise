import pytest
from products.models import Product
from tests.conftest import checkout_payload


@pytest.mark.django_db
def test_checkout_returns_unit_price_and_line_total(auth_client, user, fixed_discount):
    product = Product.objects.create(
        name="Test product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    fixed_discount(product=product, value="150.00")

    # Ensure cart exists
    auth_client.get("/api/v1/cart/")

    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2},
        format="json",
    )

    response = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email),
        format="json",
    )
    assert response.status_code == 201

    data = response.json()
    item = data["items"][0]

    # New FE-friendly contract (will be RED until PR3)
    assert item["unit_price"] == "100.00"
    assert item["quantity"] == 2
    assert item["line_total"] == "0.00"
    assert data["total"] == "0.00"
