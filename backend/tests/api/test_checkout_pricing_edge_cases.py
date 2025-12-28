import pytest
from products.models import Product
from discounts.models import Discount
from datetime import date
from decimal import Decimal


# Test for fixed discount greater than product price
@pytest.mark.django_db
def test_fixed_discount_greater_than_product_price_clamps_to_zero(auth_client):
    product = Product.objects.create(
        name="Cheap Product",
        price=Decimal("10.00"),
        stock_quantity=10,
        is_active=True,
    )

    Discount.objects.create(
        product=product,
        discount_type=Discount.FIXED,
        value=Decimal("50.00"),
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/")
    data = response.json()

    assert response.status_code == 201
    assert data["total_price"] == "0.00"


# Test for multiple discounts on the same product
@pytest.mark.django_db
def test_only_one_discount_is_applied_per_product(auth_client):
    product = Product.objects.create(
        name="Product",
        price=Decimal("100.00"),
        stock_quantity=10,
        is_active=True,
    )

    Discount.objects.create(
        product=product,
        discount_type=Discount.PERCENT,
        value=Decimal("10.00"),
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    Discount.objects.create(
        product=product,
        discount_type=Discount.FIXED,
        value=Decimal("20.00"),
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/")
    data = response.json()

    assert data["total_price"] == "80.00"  # FIXED wins


# Test for discount not applied when product is unavailable
@pytest.mark.django_db
def test_discount_not_applied_when_product_is_unavailable(auth_client):
    product = Product.objects.create(
        name="Unavailable Product",
        price=Decimal("100.00"),
        stock_quantity=0,
        is_active=True,
    )

    Discount.objects.create(
        product=product,
        discount_type=Discount.PERCENT,
        value=Decimal("50.00"),
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today(),
    )

    auth_client.get("/api/v1/cart/")
    response = auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    assert response.status_code == 409


# Test for price rounding consistency
@pytest.mark.django_db
def test_price_rounding_is_consistent(auth_client):
    product = Product.objects.create(
        name="Rounding Product",
        price=Decimal("33.333"),
        stock_quantity=10,
        is_active=True,
    )

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 3},
        format="json",
    )

    response = auth_client.post("/api/v1/cart/checkout/")
    data = response.json()

    print(f"\nStatus code: {response.status_code}")
    print(f"Response data: {data}")

    assert response.status_code == 201, response.json()
    assert data["total_price"] == "99.99"


# Test for price change between adding to cart and checkout
@pytest.mark.django_db
def test_price_change_after_add_to_cart_does_not_affect_checkout(auth_client):
    product = Product.objects.create(
        name="Dynamic Price Product",
        price=Decimal("100.00"),
        stock_quantity=10,
        is_active=True,
    )

    auth_client.get("/api/v1/cart/")
    auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    # price change after item added
    product.price = Decimal("200.00")
    product.save()

    response = auth_client.post("/api/v1/cart/checkout/")
    data = response.json()

    assert data["total_price"] == "100.00"
