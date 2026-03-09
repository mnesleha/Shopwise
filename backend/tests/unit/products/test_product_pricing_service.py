"""Unit tests for Phase 1 pricing service foundation.

Covers:
- resolve_tax: correct net/tax/gross for standard, reduced and zero rate
- resolve_tax: None tax_class treated as 0 %
- resolve_tax: missing rate on TaxClass treated as 0 %
- resolve_tax: rounding behaviour follow ROUND_HALF_UP
- ProductPricingResult: from_taxed_money helper
- get_product_pricing: structured result for a fully-configured product
- get_product_pricing: returns None when price_net_amount is not set
- get_product_pricing: zero-rate tax class produces net == gross
- get_product_pricing: different tax classes produce different gross amounts
"""
from decimal import Decimal

import pytest
from prices import Money, TaxedMoney

from products.models import Product, TaxClass
from products.services.tax_resolver import resolve_tax
from products.services.pricing import ProductPricingResult, get_product_pricing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tax_class(name: str, code: str, rate=None, save: bool = True) -> TaxClass:
    tc = TaxClass(name=name, code=code, rate=rate)
    if save:
        tc.save()
    return tc


def _product(price_net_amount=None, currency="EUR", tax_class=None, save: bool = True) -> Product:
    p = Product(
        name="Test product",
        price=Decimal("9.99"),
        stock_quantity=1,
        price_net_amount=price_net_amount,
        currency=currency,
        tax_class=tax_class,
    )
    if save:
        p.save()
    return p


# ---------------------------------------------------------------------------
# resolve_tax — pure function, no DB needed
# ---------------------------------------------------------------------------


def test_resolve_tax_standard_rate():
    """23 % on 100.00 → gross = 123.00, tax = 23.00."""
    tc = _tax_class("Standard", "standard", rate=Decimal("23"), save=False)
    result = resolve_tax(net_amount=Decimal("100.00"), currency="EUR", tax_class=tc)

    assert isinstance(result, TaxedMoney)
    assert result.net == Money(Decimal("100.00"), "EUR")
    assert result.gross == Money(Decimal("123.00"), "EUR")
    assert result.tax == Money(Decimal("23.00"), "EUR")


def test_resolve_tax_reduced_rate():
    """8 % on 50.00 → gross = 54.00, tax = 4.00."""
    tc = _tax_class("Reduced", "reduced", rate=Decimal("8"), save=False)
    result = resolve_tax(net_amount=Decimal("50.00"), currency="EUR", tax_class=tc)

    assert result.gross == Money(Decimal("54.00"), "EUR")
    assert result.tax == Money(Decimal("4.00"), "EUR")


def test_resolve_tax_zero_rate():
    """0 % explicitly set → gross == net, tax == 0."""
    tc = _tax_class("Zero", "zero", rate=Decimal("0"), save=False)
    result = resolve_tax(net_amount=Decimal("19.99"), currency="EUR", tax_class=tc)

    assert result.net == result.gross
    assert result.tax == Money(Decimal("0.00"), "EUR")


def test_resolve_tax_no_tax_class():
    """No TaxClass supplied → 0 % rate, gross == net."""
    result = resolve_tax(net_amount=Decimal("29.99"), currency="USD", tax_class=None)

    assert result.net == Money(Decimal("29.99"), "USD")
    assert result.gross == Money(Decimal("29.99"), "USD")
    assert result.tax == Money(Decimal("0.00"), "USD")


def test_resolve_tax_tax_class_without_rate():
    """TaxClass with rate=None → treated as 0 %, gross == net."""
    tc = _tax_class("No rate", "no_rate", rate=None, save=False)
    result = resolve_tax(net_amount=Decimal("10.00"), currency="PLN", tax_class=tc)

    assert result.gross == result.net


def test_resolve_tax_rounding():
    """Fractional gross is rounded ROUND_HALF_UP to 2 decimal places."""
    # 23 % on 9.99 = 12.2877 → rounds to 12.29
    tc = _tax_class("Standard", "standard", rate=Decimal("23"), save=False)
    result = resolve_tax(net_amount=Decimal("9.99"), currency="EUR", tax_class=tc)

    assert result.gross == Money(Decimal("12.29"), "EUR")
    assert result.tax == Money(Decimal("2.30"), "EUR")


def test_resolve_tax_currency_preserved():
    """Currency must be preserved in both net and gross Money instances."""
    tc = _tax_class("Standard", "standard", rate=Decimal("23"), save=False)
    result = resolve_tax(net_amount=Decimal("100.00"), currency="GBP", tax_class=tc)

    assert result.net.currency == "GBP"
    assert result.gross.currency == "GBP"


# ---------------------------------------------------------------------------
# ProductPricingResult
# ---------------------------------------------------------------------------


def test_product_pricing_result_from_taxed_money():
    net = Money(Decimal("10.00"), "EUR")
    gross = Money(Decimal("12.30"), "EUR")
    taxed = TaxedMoney(net=net, gross=gross)

    result = ProductPricingResult.from_taxed_money(taxed, tax_rate=Decimal("23"))

    assert result.net == net
    assert result.gross == gross
    assert result.tax == Money(Decimal("2.30"), "EUR")
    assert result.currency == "EUR"
    assert result.tax_rate == Decimal("23")


# ---------------------------------------------------------------------------
# get_product_pricing — requires DB
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_product_pricing_returns_none_when_no_net_amount():
    """Products not yet migrated to new pricing return None."""
    product = _product(price_net_amount=None)
    assert get_product_pricing(product) is None


@pytest.mark.django_db
def test_get_product_pricing_no_tax_class():
    """Product without TaxClass → pricing result with 0 % tax."""
    product = _product(price_net_amount=Decimal("50.00"), currency="EUR", tax_class=None)
    result = get_product_pricing(product)

    assert result is not None
    assert result.net == Money(Decimal("50.00"), "EUR")
    assert result.gross == Money(Decimal("50.00"), "EUR")
    assert result.tax == Money(Decimal("0.00"), "EUR")
    assert result.tax_rate == Decimal("0")


@pytest.mark.django_db
def test_get_product_pricing_with_standard_tax_class():
    """23 % TaxClass assignment produces correct breakdown."""
    tc = _tax_class("Standard", "standard_v2", rate=Decimal("23"))
    product = _product(price_net_amount=Decimal("100.00"), currency="EUR", tax_class=tc)

    result = get_product_pricing(product)

    assert result.net == Money(Decimal("100.00"), "EUR")
    assert result.gross == Money(Decimal("123.00"), "EUR")
    assert result.tax == Money(Decimal("23.00"), "EUR")
    assert result.tax_rate == Decimal("23")
    assert result.currency == "EUR"


@pytest.mark.django_db
def test_get_product_pricing_zero_rate_class():
    """Zero-rate TaxClass produces gross == net."""
    tc = _tax_class("Zero Rate", "zero_v2", rate=Decimal("0"))
    product = _product(price_net_amount=Decimal("19.99"), currency="EUR", tax_class=tc)

    result = get_product_pricing(product)

    assert result.gross == result.net
    assert result.tax_rate == Decimal("0")


@pytest.mark.django_db
def test_get_product_pricing_different_classes_produce_different_gross():
    """Different TaxClass rates produce different gross amounts for the same net."""
    tc_standard = _tax_class("Standard 23", "s23", rate=Decimal("23"))
    tc_reduced = _tax_class("Reduced 8", "r8", rate=Decimal("8"))

    p_std = _product(price_net_amount=Decimal("100.00"), tax_class=tc_standard)
    p_red = _product(price_net_amount=Decimal("100.00"), tax_class=tc_reduced)

    r_std = get_product_pricing(p_std)
    r_red = get_product_pricing(p_red)

    assert r_std.gross > r_red.gross
    assert r_std.gross == Money(Decimal("123.00"), "EUR")
    assert r_red.gross == Money(Decimal("108.00"), "EUR")


@pytest.mark.django_db
def test_get_product_pricing_result_is_immutable():
    """ProductPricingResult must be frozen (immutable dataclass)."""
    product = _product(price_net_amount=Decimal("10.00"))
    result = get_product_pricing(product)

    with pytest.raises((AttributeError, TypeError)):
        result.net = Money(Decimal("99.00"), "EUR")  # type: ignore[misc]
