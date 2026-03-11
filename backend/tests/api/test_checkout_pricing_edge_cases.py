"""Checkout pricing edge-case tests — Phase 3 rewrite.

Prior to Phase 3 these tests drove the legacy ``calculate_price`` / ``Discount``
model path.  They have been rewritten to exercise the current pricing pipeline
(``get_cart_pricing`` → ``get_product_pricing`` → ``resolve_line_promotion``).

The old ``Discount``-model tests have been retired in favour of ``Promotion``-model
equivalents.  A separate test covers the unmigrated-product fallback path
(products whose ``price_net_amount`` is not yet set).
"""
import pytest
from decimal import Decimal

from products.models import Product
from discounts.models import Promotion, PromotionAmountScope, PromotionProduct, PromotionType
from tests.conftest import checkout_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _product(*, name: str, price_net: Decimal, stock: int = 10) -> Product:
    """Create a migrated product (price_net_amount set, EUR, no tax)."""
    return Product.objects.create(
        name=name,
        price=price_net,
        stock_quantity=stock,
        is_active=True,
        price_net_amount=price_net,
        currency="EUR",
    )


def _promotion_product(
    product: Product,
    *,
    code: str,
    promo_type: str,
    value: Decimal,
    priority: int = 5,
    amount_scope: str = PromotionAmountScope.GROSS,
) -> Promotion:
    promo = Promotion.objects.create(
        name=f"Promo {code}",
        code=code,
        type=promo_type,
        value=value,
        priority=priority,
        is_active=True,
        amount_scope=amount_scope,
    )
    PromotionProduct.objects.create(promotion=promo, product=product)
    return promo


def _add_to_cart(client, product: Product, quantity: int = 1):
    client.get("/api/v1/cart/")
    return client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": quantity},
        format="json",
    )


# ---------------------------------------------------------------------------
# Fixed promotion clamped at zero when its value exceeds the product price
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_fixed_promotion_greater_than_price_clamps_to_zero(auth_client):
    """A FIXED GROSS promotion larger than the product price produces a 0.00 total."""
    product = _product(name="Cheap Product", price_net=Decimal("10.00"))
    _promotion_product(
        product,
        code="big-fixed-promo",
        promo_type=PromotionType.FIXED,
        value=Decimal("50.00"),
        amount_scope=PromotionAmountScope.GROSS,
    )

    _add_to_cart(auth_client, product)
    response = auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    data = response.json()

    assert response.status_code == 201
    assert data["total"] == "0.00"


# ---------------------------------------------------------------------------
# Highest-priority promotion wins when several are applicable
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_higher_priority_promotion_wins_at_checkout(auth_client):
    """When two promotions target the same product the one with higher priority is used.

    FIXED GROSS €20 (priority=10) beats PERCENT 10 % (priority=5).
    Product net €100, no tax → discounted gross 80 → total €80.00.
    The applied discount is propagated to the order item snapshot.
    """
    product = _product(name="Contested Product", price_net=Decimal("100.00"))
    _promotion_product(
        product,
        code="low-prio-pct",
        promo_type=PromotionType.PERCENT,
        value=Decimal("10.00"),
        priority=5,
    )
    _promotion_product(
        product,
        code="high-prio-fixed",
        promo_type=PromotionType.FIXED,
        value=Decimal("20.00"),
        priority=10,
        amount_scope=PromotionAmountScope.GROSS,
    )

    _add_to_cart(auth_client, product)
    response = auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    data = response.json()

    assert response.status_code == 201
    assert data["total"] == "80.00"
    item = data["items"][0]
    assert item["discount"]["type"] == "FIXED"
    assert item["discount"]["value"] == "20.00"


# ---------------------------------------------------------------------------
# Out-of-stock product cannot be added to the cart
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_out_of_stock_product_cannot_be_added_to_cart(auth_client):
    """POST to /cart/items/ returns 409 when the product has zero stock."""
    product = Product.objects.create(
        name="Unavailable Product",
        price=Decimal("100.00"),
        stock_quantity=0,
        is_active=True,
    )
    auth_client.get("/api/v1/cart/")
    response = auth_client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Price rounding is consistent in the new pipeline
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_price_rounding_is_consistent(auth_client):
    """Line total is computed as round(unit_gross × qty), not sum-of-rounded-units."""
    product = _product(name="Rounding Product", price_net=Decimal("33.33"))

    _add_to_cart(auth_client, product, quantity=3)
    response = auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")

    assert response.status_code == 201
    data = response.json()
    assert data["total"] == "99.99"


# ---------------------------------------------------------------------------
# Checkout uses LIVE pricing — price_at_add_time is NOT the checkout authority
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_checkout_uses_live_pricing_not_snapshot(auth_client):
    """Checkout uses the current product price at checkout time (live pipeline).

    After Phase 3 the authoritative pricing source is the current pricing
    pipeline (get_product_pricing), not the snapshotted price_at_add_time.
    If price_net_amount changes between add-to-cart and checkout, the
    checkout reflects the current price.

    price_at_add_time remains on the CartItem record; it will be used for
    customer-facing price-change detection in a future slice.
    """
    product = _product(name="Dynamic Price Product", price_net=Decimal("100.00"))
    _add_to_cart(auth_client, product, quantity=1)

    # Merchant raises the price after the customer adds to cart.
    product.price = Decimal("200.00")
    product.price_net_amount = Decimal("200.00")
    product.save()

    response = auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    data = response.json()

    assert response.status_code == 201
    # Checkout now uses the live price via the current pricing pipeline.
    assert data["total"] == "200.00"


# ---------------------------------------------------------------------------
# Unmigrated products fall back to price_at_add_time (no live pipeline path)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_unmigrated_product_falls_back_to_price_at_add_time(auth_client):
    """Products without price_net_amount fall back to price_at_add_time at checkout.

    This is a temporary backward-compat path retained while products are
    migrated to the new pricing model.  The fallback uses the snapshotted
    gross price without any discount applied.
    """
    # Legacy product: only the ``price`` field is set (price_net_amount is NULL).
    product = Product.objects.create(
        name="Legacy Product",
        price=Decimal("50.00"),
        stock_quantity=10,
        is_active=True,
        # price_net_amount intentionally omitted
    )

    _add_to_cart(auth_client, product, quantity=1)

    # Merchant changes the legacy price field after the customer adds to cart.
    product.price = Decimal("99.00")
    product.save()

    response = auth_client.post("/api/v1/cart/checkout/", checkout_payload(), format="json")
    data = response.json()

    # Fallback path: price_at_add_time (50.00) is used, not the current price.
    assert response.status_code == 201
    assert data["total"] == "50.00"
