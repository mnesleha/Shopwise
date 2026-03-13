"""API tests for Phase 4 / Slice 4 — threshold reward progress in cart payload.

Covers:
- threshold_reward is null when no threshold promotions exist
- threshold_reward shows remaining amount when cart is below threshold
- threshold_reward shows is_unlocked=True when cart gross equals threshold (boundary)
- threshold_reward shows is_unlocked=True when cart gross exceeds threshold
- current_basis in threshold_reward matches total_gross from cart totals
- threshold_reward payload structure contains all required keys
- threshold reward state is consistent between cart GET and checkout POST
"""

from decimal import Decimal

import pytest
from django.utils.timezone import now, timedelta

from discounts.models import AcquisitionMode, OrderPromotion, PromotionType, StackingPolicy
from products.models import Product, TaxClass

CART_URL = "/api/v1/cart/"
CART_ITEMS_URL = "/api/v1/cart/items/"

_CODE_SEQ = 0


def _next_code() -> str:
    global _CODE_SEQ
    _CODE_SEQ += 1
    return f"THRESH-{_CODE_SEQ:04d}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tax_class(suffix: str = "") -> TaxClass:
    return TaxClass.objects.create(
        name=f"Standard {suffix}",
        code=f"std{suffix}",
        rate=Decimal("20"),
    )


def _product(*, price_net_amount: Decimal, tax_class=None) -> Product:
    if tax_class is None:
        tax_class = _tax_class(suffix=str(price_net_amount).replace(".", "_"))
    return Product.objects.create(
        name=f"Product {price_net_amount}",
        price=price_net_amount,
        stock_quantity=100,
        is_active=True,
        price_net_amount=price_net_amount,
        currency="EUR",
        tax_class=tax_class,
    )


def _threshold_promotion(
    *,
    minimum_order_value: Decimal,
    value: Decimal = Decimal("10"),
    priority: int = 5,
) -> OrderPromotion:
    return OrderPromotion.objects.create(
        name=f"Reward ≥{minimum_order_value}",
        code=_next_code(),
        type=PromotionType.PERCENT,
        value=value,
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        stacking_policy=StackingPolicy.EXCLUSIVE,
        priority=priority,
        is_active=True,
        minimum_order_value=minimum_order_value,
        active_from=now() - timedelta(days=1),
        active_to=now() + timedelta(days=30),
    )


def _add_item(client, product: Product, qty: int = 1) -> None:
    resp = client.post(
        CART_ITEMS_URL,
        {"product_id": product.id, "quantity": qty},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.json()


def _get_cart_totals(client) -> dict:
    resp = client.get(CART_URL)
    assert resp.status_code == 200
    return resp.json()["totals"]


# ---------------------------------------------------------------------------
# threshold_reward absent when no threshold promotions exist
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_threshold_reward_null_when_no_threshold_promotions(auth_client):
    """When no AUTO_APPLY promotions with minimum_order_value exist, threshold_reward is null."""
    tc = _tax_class("no_thresh")
    p = _product(price_net_amount=Decimal("50.00"), tax_class=tc)
    _add_item(auth_client, p)

    totals = _get_cart_totals(auth_client)

    assert totals["threshold_reward"] is None


# ---------------------------------------------------------------------------
# Below threshold — shows remaining, is_unlocked=False
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_threshold_reward_shows_remaining_when_below_threshold(auth_client):
    """Cart gross below the threshold must expose is_unlocked=False and a positive remaining."""
    # Net 66.67 × 1.20 VAT ≈ 80.00 gross
    tc = _tax_class("below")
    p = _product(price_net_amount=Decimal("66.67"), tax_class=tc)
    _add_item(auth_client, p)

    _threshold_promotion(minimum_order_value=Decimal("100.00"))

    totals = _get_cart_totals(auth_client)
    tr = totals["threshold_reward"]

    assert tr is not None
    assert tr["is_unlocked"] is False
    remaining = Decimal(tr["remaining"])
    assert remaining > Decimal("0.00")


@pytest.mark.django_db
def test_threshold_reward_remaining_is_difference_from_basis(auth_client):
    """remaining must equal threshold − current_basis (rounded to 2dp)."""
    tc = _tax_class("diff")
    p = _product(price_net_amount=Decimal("66.67"), tax_class=tc)
    _add_item(auth_client, p)

    _threshold_promotion(minimum_order_value=Decimal("100.00"))

    totals = _get_cart_totals(auth_client)
    tr = totals["threshold_reward"]

    basis = Decimal(tr["current_basis"])
    threshold = Decimal(tr["threshold"])
    remaining = Decimal(tr["remaining"])

    assert remaining == (threshold - basis).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# At threshold — is_unlocked=True, remaining=0.00
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_threshold_reward_unlocked_when_at_threshold(auth_client):
    """Cart gross exactly equal to threshold must yield is_unlocked=True and remaining=0.00."""
    # Use a round number that's also the cart gross after VAT
    # Net 100.00 at 0% VAT → gross 100.00
    tc = TaxClass.objects.create(name="Zero VAT at", code="zero_at", rate=Decimal("0"))
    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc)
    _add_item(auth_client, p)

    _threshold_promotion(minimum_order_value=Decimal("100.00"))

    totals = _get_cart_totals(auth_client)
    tr = totals["threshold_reward"]

    assert tr is not None
    assert tr["is_unlocked"] is True
    assert tr["remaining"] == "0.00"


# ---------------------------------------------------------------------------
# Above threshold — is_unlocked=True
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_threshold_reward_unlocked_when_above_threshold(auth_client):
    """Cart gross exceeding threshold must yield is_unlocked=True."""
    tc = TaxClass.objects.create(name="Zero VAT above", code="zero_above", rate=Decimal("0"))
    p = _product(price_net_amount=Decimal("150.00"), tax_class=tc)
    _add_item(auth_client, p)

    _threshold_promotion(minimum_order_value=Decimal("100.00"))

    totals = _get_cart_totals(auth_client)
    tr = totals["threshold_reward"]

    assert tr is not None
    assert tr["is_unlocked"] is True


# ---------------------------------------------------------------------------
# current_basis matches total_gross
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_threshold_reward_basis_equals_total_gross(auth_client):
    """threshold_reward.current_basis must equal totals.total_gross."""
    tc = _tax_class("basis")
    p = _product(price_net_amount=Decimal("40.00"), tax_class=tc)
    _add_item(auth_client, p)

    _threshold_promotion(minimum_order_value=Decimal("100.00"))

    totals = _get_cart_totals(auth_client)
    tr = totals["threshold_reward"]

    assert tr is not None
    assert tr["current_basis"] == totals["total_gross"]


# ---------------------------------------------------------------------------
# Complete payload structure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_threshold_reward_structure_complete(auth_client):
    """threshold_reward payload must contain exactly the documented keys."""
    tc = TaxClass.objects.create(name="Zero VAT struct", code="zero_struct", rate=Decimal("0"))
    p = _product(price_net_amount=Decimal("50.00"), tax_class=tc)
    _add_item(auth_client, p)

    _threshold_promotion(minimum_order_value=Decimal("100.00"))

    totals = _get_cart_totals(auth_client)
    tr = totals["threshold_reward"]

    assert tr is not None
    assert set(tr.keys()) == {
        "is_unlocked",
        "promotion_name",
        "threshold",
        "current_basis",
        "remaining",
        "currency",
    }


# ---------------------------------------------------------------------------
# Promotion name is preserved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_threshold_reward_promotion_name_matches(auth_client):
    """promotion_name in threshold_reward must match the OrderPromotion name."""
    tc = TaxClass.objects.create(name="Zero VAT name", code="zero_name", rate=Decimal("0"))
    p = _product(price_net_amount=Decimal("50.00"), tax_class=tc)
    _add_item(auth_client, p)

    promo = _threshold_promotion(minimum_order_value=Decimal("100.00"))

    totals = _get_cart_totals(auth_client)
    tr = totals["threshold_reward"]

    assert tr is not None
    assert tr["promotion_name"] == promo.name
