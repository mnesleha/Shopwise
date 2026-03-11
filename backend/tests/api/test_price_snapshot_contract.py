"""Checkout API response contract test — Phase 3.

Verifies that the checkout response surface (unit_price, line_total, total)
reflects the current pricing pipeline output, not the pre-Phase-3 snapshot
semantics.

Phase 3 semantics:
- unit_price  = discounted gross per unit (from the current pricing pipeline)
- line_total  = unit_price × quantity
- discount    = promotion snapshot when a promotion was applied
- total       = sum of all line_totals
"""
import pytest
from decimal import Decimal
from products.models import Product
from discounts.models import Promotion, PromotionAmountScope, PromotionProduct, PromotionType
from tests.conftest import checkout_payload


@pytest.mark.django_db
def test_checkout_returns_unit_price_and_line_total(auth_client, user):
    """Checkout response carries per-unit and per-line totals from the current pipeline.

    Migrated product (price_net_amount set), PERCENT 20 % promotion applied.
    net €100, no tax → discounted gross €80 per unit; qty=2 → line_total €160.
    """
    product = Product.objects.create(
        name="Test product",
        price=Decimal("100.00"),
        stock_quantity=10,
        is_active=True,
        price_net_amount=Decimal("100.00"),
        currency="EUR",
    )
    promo = Promotion.objects.create(
        name="20 pct off",
        code="test-20pct",
        type=PromotionType.PERCENT,
        value=Decimal("20.00"),
        is_active=True,
    )
    PromotionProduct.objects.create(promotion=promo, product=product)

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

    # Phase 3 contract: unit_price is the discounted gross (pipeline output).
    assert item["unit_price"] == "80.00"
    assert item["quantity"] == 2
    assert item["line_total"] == "160.00"
    assert data["total"] == "160.00"
    assert item["discount"]["type"] == "PERCENT"
