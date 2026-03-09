"""API tests for structured product pricing exposure (Phase 1 Slice 3).

Covers:
- ``pricing`` field present in list response
- ``pricing`` field present in detail response
- Correct net / gross / tax / currency / tax_rate values with a tax class
- ``pricing`` is null for products without ``price_net_amount`` (migration state)
- Zero-rate tax class produces gross == net
- Different tax classes produce different gross values
- Legacy ``price`` field still present in both list and detail (backward compat)
- Behaviour is consistent between list and detail endpoints
"""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from products.models import Product, TaxClass

LIST_URL = "/api/v1/products/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tax_class(*, name: str, code: str, rate=None) -> TaxClass:
    return TaxClass.objects.create(name=name, code=code, rate=rate)


def _product(*, name: str = "Test Product", price_net_amount=None, currency: str = "EUR",
             tax_class=None) -> Product:
    return Product.objects.create(
        name=name,
        # Legacy field required by model until migration is complete.
        price=price_net_amount if price_net_amount is not None else Decimal("9.99"),
        stock_quantity=10,
        is_active=True,
        price_net_amount=price_net_amount,
        currency=currency,
        tax_class=tax_class,
    )


def _detail_url(product_id: int) -> str:
    return f"/api/v1/products/{product_id}/"


def _client() -> APIClient:
    return APIClient()


# ---------------------------------------------------------------------------
# Pricing field presence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_field_present_in_list_response():
    """`pricing` key must appear in every item of the catalogue list."""
    _product(name="P1", price_net_amount=Decimal("50.00"))
    resp = _client().get(LIST_URL)
    assert resp.status_code == 200
    item = resp.json()["results"][0]
    assert "pricing" in item


@pytest.mark.django_db
def test_pricing_field_present_in_detail_response():
    """`pricing` key must appear in the product detail response."""
    p = _product(name="P1", price_net_amount=Decimal("50.00"))
    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    assert "pricing" in resp.json()


# ---------------------------------------------------------------------------
# pricing == null when price_net_amount not set
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_is_null_when_no_price_net_amount_list():
    """Products without price_net_amount return pricing=null in the list."""
    _product(name="Legacy", price_net_amount=None)
    resp = _client().get(LIST_URL)
    assert resp.status_code == 200
    item = resp.json()["results"][0]
    assert item["pricing"] is None


@pytest.mark.django_db
def test_pricing_is_null_when_no_price_net_amount_detail():
    """Products without price_net_amount return pricing=null in the detail."""
    p = _product(name="Legacy", price_net_amount=None)
    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    assert resp.json()["pricing"] is None


# ---------------------------------------------------------------------------
# pricing values with standard tax class
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_values_with_23pct_tax_class_in_list():
    """23 % TaxClass → gross=123.00, tax=23.00 for net=100.00 in list."""
    tc = _tax_class(name="Standard", code="std_list", rate=Decimal("23"))
    _product(name="Mouse", price_net_amount=Decimal("100.00"), tax_class=tc)

    resp = _client().get(LIST_URL)
    assert resp.status_code == 200
    pricing = resp.json()["results"][0]["pricing"]

    assert pricing["net"] == "100.00"
    assert pricing["gross"] == "123.00"
    assert pricing["tax"] == "23.00"
    assert pricing["currency"] == "EUR"
    assert pricing["tax_rate"] == "23"


@pytest.mark.django_db
def test_pricing_values_with_23pct_tax_class_in_detail():
    """23 % TaxClass → gross=123.00, tax=23.00 for net=100.00 in detail."""
    tc = _tax_class(name="Standard", code="std_detail", rate=Decimal("23"))
    p = _product(name="Mouse", price_net_amount=Decimal("100.00"), tax_class=tc)

    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["net"] == "100.00"
    assert pricing["gross"] == "123.00"
    assert pricing["tax"] == "23.00"
    assert pricing["currency"] == "EUR"
    assert pricing["tax_rate"] == "23"


# ---------------------------------------------------------------------------
# pricing with no tax class (0 % implicit)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_no_tax_class_gross_equals_net():
    """No TaxClass → gross == net, tax == 0, tax_rate == '0'."""
    p = _product(name="Untaxed", price_net_amount=Decimal("29.99"), tax_class=None)
    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["net"] == pricing["gross"]
    assert pricing["tax"] == "0.00"
    assert pricing["tax_rate"] == "0"


@pytest.mark.django_db
def test_pricing_zero_rate_class_gross_equals_net():
    """Explicit zero-rate TaxClass → gross == net."""
    tc = _tax_class(name="Zero Rate", code="zero_api", rate=Decimal("0"))
    p = _product(name="Zero-rated product", price_net_amount=Decimal("15.00"), tax_class=tc)
    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]

    assert pricing["gross"] == pricing["net"]
    assert pricing["tax_rate"] == "0"


# ---------------------------------------------------------------------------
# Different tax classes produce different gross
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_different_tax_classes_produce_different_gross_in_list():
    """Standard vs reduced rate on equal net amount → different gross in list."""
    tc_std = _tax_class(name="Standard 23", code="std23_list", rate=Decimal("23"))
    tc_red = _tax_class(name="Reduced 8", code="red8_list", rate=Decimal("8"))

    _product(name="Standard product", price_net_amount=Decimal("100.00"), tax_class=tc_std)
    _product(name="Reduced product", price_net_amount=Decimal("100.00"), tax_class=tc_red)

    resp = _client().get(LIST_URL)
    assert resp.status_code == 200
    results = resp.json()["results"]

    pricings = {item["name"]: item["pricing"] for item in results}
    assert pricings["Standard product"]["gross"] == "123.00"
    assert pricings["Reduced product"]["gross"] == "108.00"


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_currency_matches_product_currency():
    """`pricing.currency` must match the product's currency field."""
    tc = _tax_class(name="Standard", code="std_usd", rate=Decimal("20"))
    p = _product(name="USD Product", price_net_amount=Decimal("50.00"), currency="USD", tax_class=tc)
    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    assert resp.json()["pricing"]["currency"] == "USD"


# ---------------------------------------------------------------------------
# Backward compatibility: legacy price field
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_legacy_price_field_still_present_in_list():
    """Legacy `price` field must still be present in list responses."""
    _product(name="Compat product", price_net_amount=Decimal("19.99"))
    resp = _client().get(LIST_URL)
    assert resp.status_code == 200
    item = resp.json()["results"][0]
    assert "price" in item


@pytest.mark.django_db
def test_legacy_price_field_still_present_in_detail():
    """Legacy `price` field must still be present in detail responses."""
    p = _product(name="Compat product", price_net_amount=Decimal("19.99"))
    resp = _client().get(_detail_url(p.id))
    assert resp.status_code == 200
    assert "price" in resp.json()


# ---------------------------------------------------------------------------
# Consistency: list and detail return the same pricing for the same product
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_consistent_between_list_and_detail():
    """The `pricing` payload must be identical in list and detail for the same product."""
    tc = _tax_class(name="Standard", code="std_cons", rate=Decimal("23"))
    p = _product(name="Consistent product", price_net_amount=Decimal("49.99"), tax_class=tc)

    list_resp = _client().get(LIST_URL)
    detail_resp = _client().get(_detail_url(p.id))

    assert list_resp.status_code == 200
    assert detail_resp.status_code == 200

    list_pricing = list_resp.json()["results"][0]["pricing"]
    detail_pricing = detail_resp.json()["pricing"]

    assert list_pricing == detail_pricing
