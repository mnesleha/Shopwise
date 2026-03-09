"""Integration tests for django-prices model layer (Phase 1 corrective slice).

Covers:
- price_net MoneyField accessor: correct Money instance / None when unset
- price_gross MoneyField accessor: correct Money instance after save
- taxed_price TaxedMoneyField accessor: correct TaxedMoney / None when unset
- price_gross_amount synchronised by Product.save() from the tax resolver
- price_gross_amount re-synchronised when tax_class changes
- price_gross_amount re-synchronised when price_net_amount changes
- MoneyField __set__ assignment round-trips through to amount + currency fields
- pricing service still returns correct result (regression guard)
- API pricing output unchanged (regression guard)
"""
from decimal import Decimal

import pytest
from prices import Money, TaxedMoney
from rest_framework.test import APIClient

from products.models import Product, TaxClass
from products.services.pricing import get_product_pricing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tc(code: str, *, rate=None) -> TaxClass:
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


# ---------------------------------------------------------------------------
# price_net MoneyField
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_price_net_returns_money_instance_when_set():
    """price_net must return a prices.Money when price_net_amount is set."""
    p = _product(price_net_amount=Decimal("50.00"), currency="EUR")
    assert isinstance(p.price_net, Money)
    assert p.price_net.amount == Decimal("50.00")
    assert p.price_net.currency == "EUR"


@pytest.mark.django_db
def test_price_net_returns_none_when_amount_unset():
    """price_net must return None when price_net_amount is None."""
    p = _product(price_net_amount=None)
    assert p.price_net is None


@pytest.mark.django_db
def test_price_net_currency_follows_currency_field():
    """price_net.currency must match the product's currency field."""
    p = _product(price_net_amount=Decimal("20.00"), currency="USD")
    assert p.price_net.currency == "USD"


@pytest.mark.django_db
def test_price_net_assignment_via_descriptor():
    """Assigning a Money to price_net must write through to price_net_amount and currency."""
    p = _product(price_net_amount=Decimal("10.00"), currency="EUR")
    p.price_net = Money(Decimal("99.00"), "GBP")
    assert p.price_net_amount == Decimal("99.00")
    assert p.currency == "GBP"


# ---------------------------------------------------------------------------
# price_gross_amount synchronisation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_price_gross_amount_computed_on_save_with_tax_class():
    """price_gross_amount must be re-computed by save() using the tax resolver."""
    tc = _tc("std_int", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc)
    p.refresh_from_db()
    assert p.price_gross_amount == Decimal("123.00")


@pytest.mark.django_db
def test_price_gross_amount_is_none_when_no_net_amount():
    """price_gross_amount must be None when price_net_amount is not set."""
    p = _product(price_net_amount=None)
    p.refresh_from_db()
    assert p.price_gross_amount is None


@pytest.mark.django_db
def test_price_gross_amount_uses_zero_rate_when_no_tax_class():
    """Without a TaxClass save() must store gross == net (0 % implicit)."""
    p = _product(price_net_amount=Decimal("30.00"), tax_class=None)
    p.refresh_from_db()
    assert p.price_gross_amount == Decimal("30.00")


@pytest.mark.django_db
def test_price_gross_amount_recomputed_when_net_changes():
    """Updating price_net_amount and re-saving must update price_gross_amount."""
    tc = _tc("std_net_chg", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc)
    p.price_net_amount = Decimal("200.00")
    p.save()
    p.refresh_from_db()
    assert p.price_gross_amount == Decimal("246.00")


@pytest.mark.django_db
def test_price_gross_amount_recomputed_when_tax_class_changes():
    """Assigning a different TaxClass and re-saving must update price_gross_amount."""
    tc_a = _tc("tc_a_chg", rate=Decimal("23"))
    tc_b = _tc("tc_b_chg", rate=Decimal("8"))

    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc_a)
    p.refresh_from_db()
    assert p.price_gross_amount == Decimal("123.00")

    p.tax_class = tc_b
    p.save()
    p.refresh_from_db()
    assert p.price_gross_amount == Decimal("108.00")


# ---------------------------------------------------------------------------
# price_gross MoneyField
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_price_gross_returns_money_instance_after_save():
    """price_gross must return a Money with the computed gross amount."""
    tc = _tc("std_gross", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc)
    assert isinstance(p.price_gross, Money)
    assert p.price_gross.amount == Decimal("123.00")
    assert p.price_gross.currency == "EUR"


@pytest.mark.django_db
def test_price_gross_returns_none_when_unset():
    """price_gross must return None when price_gross_amount is None."""
    p = _product(price_net_amount=None)
    assert p.price_gross is None


# ---------------------------------------------------------------------------
# taxed_price TaxedMoneyField
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_taxed_price_returns_taxed_money_when_both_amounts_set():
    """taxed_price must return a TaxedMoney when net and gross are both set."""
    tc = _tc("std_taxed", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc)
    assert isinstance(p.taxed_price, TaxedMoney)


@pytest.mark.django_db
def test_taxed_price_net_matches_price_net():
    """taxed_price.net must equal price_net."""
    tc = _tc("std_t_net", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("50.00"), tax_class=tc)
    assert p.taxed_price.net == p.price_net


@pytest.mark.django_db
def test_taxed_price_gross_matches_price_gross():
    """taxed_price.gross must equal price_gross."""
    tc = _tc("std_t_gross", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("50.00"), tax_class=tc)
    assert p.taxed_price.gross == p.price_gross


@pytest.mark.django_db
def test_taxed_price_is_none_when_net_amount_unset():
    """taxed_price must be None when price_net_amount is not set."""
    p = _product(price_net_amount=None)
    assert p.taxed_price is None


@pytest.mark.django_db
def test_taxed_price_tax_component_correct():
    """taxed_price.tax (gross - net) must match the resolver's tax amount."""
    tc = _tc("std_t_tax", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc)
    assert p.taxed_price.tax == Money(Decimal("23.00"), "EUR")


# ---------------------------------------------------------------------------
# Pricing service regression guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pricing_service_still_returns_correct_breakdown():
    """get_product_pricing must still return correct net/gross/tax after model change."""
    tc = _tc("std_svc_reg", rate=Decimal("23"))
    p = _product(price_net_amount=Decimal("100.00"), tax_class=tc)

    result = get_product_pricing(p)
    assert result is not None
    assert result.net == Money(Decimal("100.00"), "EUR")
    assert result.gross == Money(Decimal("123.00"), "EUR")
    assert result.tax == Money(Decimal("23.00"), "EUR")


@pytest.mark.django_db
def test_pricing_service_and_taxed_price_agree():
    """taxed_price and get_product_pricing must agree on net and gross."""
    tc = _tc("std_agree", rate=Decimal("8"))
    p = _product(price_net_amount=Decimal("50.00"), tax_class=tc)
    result = get_product_pricing(p)

    assert p.taxed_price.net.amount == result.net.amount
    assert p.taxed_price.gross.amount == result.gross.amount


# ---------------------------------------------------------------------------
# API pricing output regression guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_api_pricing_output_unchanged_after_model_change():
    """API pricing field must still return the correct payload after model integration."""
    tc = _tc("std_api_reg", rate=Decimal("23"))
    p = _product(name="API Reg", price_net_amount=Decimal("100.00"), tax_class=tc)

    resp = APIClient().get(f"/api/v1/products/{p.id}/")
    assert resp.status_code == 200
    pricing = resp.json()["pricing"]
    # Phase 2: values live under undiscounted/discounted tiers.
    und = pricing["undiscounted"]
    assert und["net"] == "100.00"
    assert und["gross"] == "123.00"
    assert und["tax"] == "23.00"
    assert und["currency"] == "EUR"
    assert und["tax_rate"] == "23"
    # Without a promotion discounted == undiscounted.
    assert pricing["discounted"] == und


@pytest.mark.django_db
def test_api_pricing_null_for_unmigrated_product_unchanged():
    """pricing=null contract must still hold after model integration."""
    p = _product(name="Legacy API", price_net_amount=None)
    resp = APIClient().get(f"/api/v1/products/{p.id}/")
    assert resp.status_code == 200
    assert resp.json()["pricing"] is None
