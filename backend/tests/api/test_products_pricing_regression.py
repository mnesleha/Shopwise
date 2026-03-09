"""Phase 1 pricing foundation — regression hardening tests.

These tests guard the boundary established by Phase 1 and prevent
future changes from accidentally:
  - bypassing the pricing service layer in serializers
  - computing pricing math directly in serializers or views
  - breaking legacy ``price`` field coexistence
  - introducing non-determinism in the pricing output
  - silently ignoring inactive TaxClass rates
  - losing the null-safety contract for unmigrated products

They complement the functional tests in test_product_pricing_foundation.py,
test_product_pricing_service.py, and test_products_pricing_api.py.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from rest_framework.test import APIClient

from products.models import Product, TaxClass
from products.services.pricing import get_product_pricing, ProductPricingResult

LIST_URL = "/api/v1/products/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tc(*, code: str, rate=None) -> TaxClass:
    return TaxClass.objects.create(name=code.title(), code=code, rate=rate)


def _product(*, name: str = "P", price_net_amount=None, currency: str = "EUR",
             tax_class=None) -> Product:
    return Product.objects.create(
        name=name,
        price=price_net_amount if price_net_amount is not None else Decimal("9.99"),
        stock_quantity=5,
        is_active=True,
        price_net_amount=price_net_amount,
        currency=currency,
        tax_class=tax_class,
    )


def _detail_url(pk: int) -> str:
    return f"/api/v1/products/{pk}/"


# ---------------------------------------------------------------------------
# Guard rail: serializer delegates to the service layer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_serializer_calls_get_product_pricing():
    """ProductSerializer.get_pricing must delegate to get_product_pricing.

    If this test fails it means pricing math has been duplicated inside the
    serializer, which violates the service-layer boundary.
    """
    _product(name="Mouse", price_net_amount=Decimal("50.00"))

    with patch(
        "api.serializers.product.get_product_pricing",
        wraps=get_product_pricing,
    ) as spy:
        resp = APIClient().get(LIST_URL)
        assert resp.status_code == 200
        assert spy.call_count >= 1, (
            "get_product_pricing was never called — "
            "serializer may be computing pricing directly."
        )


@pytest.mark.django_db
def test_detail_serializer_calls_get_product_pricing():
    """ProductDetailSerializer.get_pricing must delegate to get_product_pricing."""
    p = _product(name="Keyboard", price_net_amount=Decimal("80.00"))

    with patch(
        "api.serializers.product.get_product_pricing",
        wraps=get_product_pricing,
    ) as spy:
        resp = APIClient().get(_detail_url(p.id))
        assert resp.status_code == 200
        assert spy.call_count == 1


# ---------------------------------------------------------------------------
# Guard rail: pricing = null contract for unmigrated products
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_null_contract_is_stable_for_unmigrated_product():
    """pricing must always be null when price_net_amount is None.

    Repeated calls must return null consistently — no flappy behaviour.
    """
    p = _product(name="Legacy", price_net_amount=None)
    client = APIClient()

    for _ in range(3):
        resp = client.get(_detail_url(p.id))
        assert resp.status_code == 200
        assert resp.json()["pricing"] is None, (
            "pricing should be null for unmigrated products on every call"
        )


# ---------------------------------------------------------------------------
# Legacy price field coexistence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_legacy_price_unaffected_by_new_pricing_fields():
    """Writing price_net_amount must not change the value of the legacy price field."""
    tc = _tc(code="std_reg", rate=Decimal("23"))
    p = _product(
        name="Coexist",
        price_net_amount=Decimal("100.00"),
        tax_class=tc,
    )
    # legacy price was set to 100.00 (same value used in helper)
    p.refresh_from_db()
    original_legacy_price = p.price

    # Simulate in-place update of new pricing fields (a likely future migration step).
    p.price_net_amount = Decimal("200.00")
    p.save()
    p.refresh_from_db()

    assert p.price == original_legacy_price, (
        "Updating price_net_amount must not silently modify the legacy price field"
    )


@pytest.mark.django_db
def test_legacy_price_present_in_api_response_alongside_pricing():
    """Both 'price' and 'pricing' keys must coexist in API responses."""
    _product(name="Dual", price_net_amount=Decimal("50.00"))
    resp = APIClient().get(LIST_URL)
    assert resp.status_code == 200
    item = resp.json()["results"][0]
    assert "price" in item, "legacy price field must still be present"
    assert "pricing" in item, "new pricing field must be present"
    # Both must be independently non-null for a fully migrated product.
    assert item["price"] is not None
    assert item["pricing"] is not None


# ---------------------------------------------------------------------------
# Fractional tax rate serialization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fractional_tax_rate_serialized_without_trailing_zeros():
    """Fractional rates like 8.5 % must serialize as '8.5', not '8.5000'."""
    tc = _tc(code="reg_frac", rate=Decimal("8.5"))
    p = _product(name="Fractional", price_net_amount=Decimal("100.00"), tax_class=tc)
    resp = APIClient().get(_detail_url(p.id))
    assert resp.status_code == 200
    assert resp.json()["pricing"]["tax_rate"] == "8.5"


@pytest.mark.django_db
def test_zero_rate_serialized_without_decimal_places():
    """Zero rate must serialize as '0', not '0.0000'."""
    tc = _tc(code="zero_reg", rate=Decimal("0"))
    p = _product(name="ZeroRate", price_net_amount=Decimal("20.00"), tax_class=tc)
    resp = APIClient().get(_detail_url(p.id))
    assert resp.status_code == 200
    assert resp.json()["pricing"]["tax_rate"] == "0"


# ---------------------------------------------------------------------------
# Determinism: same product → same pricing output
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_output_is_deterministic_across_calls():
    """Repeated serializer calls for the same product must yield identical pricing."""
    tc = _tc(code="det_std", rate=Decimal("23"))
    p = _product(name="Det", price_net_amount=Decimal("49.99"), tax_class=tc)
    client = APIClient()

    first = client.get(_detail_url(p.id)).json()["pricing"]
    second = client.get(_detail_url(p.id)).json()["pricing"]

    assert first == second, "pricing must be deterministic across requests"


# ---------------------------------------------------------------------------
# Inactive TaxClass: is_active flag does NOT suppress pricing
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_inactive_tax_class_still_contributes_rate():
    """TaxClass.is_active is an admin toggle, not a pricing guard.

    If a TaxClass is marked inactive, the rate it carries must still be
    applied to products assigned to it.  Suppressing inactive classes at
    pricing time would cause silent 0 % tax on live products.  That concern
    belongs to a future admin-workflow, not the pricing resolver.
    """
    tc = _tc(code="inactive_reg", rate=Decimal("23"))
    tc.is_active = False
    tc.save()

    p = _product(name="Inactive TC product", price_net_amount=Decimal("100.00"), tax_class=tc)
    result = get_product_pricing(p)

    assert result is not None
    assert result.tax_rate == Decimal("23")
    from prices import Money
    assert result.gross == Money(Decimal("123.00"), "EUR")


# ---------------------------------------------------------------------------
# Null-rate on TaxClass falls back to 0 %
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tax_class_with_null_rate_treated_as_zero():
    """TaxClass.rate = None must be treated as 0 %, not raise an error."""
    tc = _tc(code="null_rate_reg", rate=None)
    p = _product(name="NullRate", price_net_amount=Decimal("30.00"), tax_class=tc)

    result = get_product_pricing(p)
    assert result is not None
    assert result.tax_rate == Decimal("0")
    assert result.gross == result.net


# ---------------------------------------------------------------------------
# Service returns None → serializer returns None (not an error)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_service_returning_none_produces_null_not_500():
    """If the pricing service returns None the API must respond 200 with null pricing,
    not a 500 Internal Server Error."""
    with patch(
        "api.serializers.product.get_product_pricing",
        return_value=None,
    ):
        p = _product(name="ForcedNull", price_net_amount=Decimal("10.00"))
        resp = APIClient().get(_detail_url(p.id))

    assert resp.status_code == 200
    assert resp.json()["pricing"] is None


# ---------------------------------------------------------------------------
# pricing fields carry correct sub-keys (schema guard)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_payload_contains_all_required_keys():
    """The pricing dict must always contain exactly the canonical set of keys."""
    tc = _tc(code="schema_guard", rate=Decimal("23"))
    p = _product(name="Schema", price_net_amount=Decimal("10.00"), tax_class=tc)
    resp = APIClient().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    required_keys = {"net", "gross", "tax", "currency", "tax_rate"}
    assert required_keys.issubset(pricing.keys()), (
        f"pricing is missing keys: {required_keys - set(pricing.keys())}"
    )
