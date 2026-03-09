"""Unit tests for Phase 1 pricing foundation.

Covers:
- TaxClass model creation and string representation
- TaxClass fields (code uniqueness, is_active default)
- Product can store price_net_amount, currency, and tax_class
- TaxClass can be assigned to and retrieved from Product
- Admin registration smoke-test (model wiring)
"""
from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError

from products.admin import TaxClassAdmin, ProductAdmin
from products.models import CURRENCY_CHOICES, Product, TaxClass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(**kwargs) -> Product:
    """Return a persisted Product with sensible pricing defaults."""
    defaults = {
        "name": "Test Product",
        "price": Decimal("9.99"),
        "stock_quantity": 10,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def _make_tax_class(**kwargs) -> TaxClass:
    """Return a persisted TaxClass with sensible defaults."""
    defaults = {
        "name": "Standard Rate",
        "code": "standard",
    }
    defaults.update(kwargs)
    return TaxClass.objects.create(**defaults)


# ---------------------------------------------------------------------------
# TaxClass model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tax_class_can_be_created():
    tc = _make_tax_class(name="Reduced Rate", code="reduced")
    assert tc.pk is not None
    assert tc.name == "Reduced Rate"
    assert tc.code == "reduced"


@pytest.mark.django_db
def test_tax_class_is_active_by_default():
    tc = _make_tax_class()
    assert tc.is_active is True


@pytest.mark.django_db
def test_tax_class_str_returns_name():
    tc = _make_tax_class(name="Zero Rate", code="zero")
    assert str(tc) == "Zero Rate"


@pytest.mark.django_db
def test_tax_class_code_must_be_unique():
    _make_tax_class(name="Standard Rate", code="standard")
    with pytest.raises(Exception):
        # Duplicate code must raise an IntegrityError (wrapped by Django).
        _make_tax_class(name="Another Standard", code="standard")


@pytest.mark.django_db
def test_tax_class_description_optional():
    tc = _make_tax_class()
    assert tc.description == ""


# ---------------------------------------------------------------------------
# Product pricing foundation fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_price_net_amount_defaults_to_none():
    product = _make_product()
    assert product.price_net_amount is None


@pytest.mark.django_db
def test_product_can_store_price_net_amount():
    product = _make_product(price_net_amount=Decimal("19.99"))
    product.refresh_from_db()
    assert product.price_net_amount == Decimal("19.99")


@pytest.mark.django_db
def test_product_currency_defaults_to_eur():
    product = _make_product()
    assert product.currency == "EUR"


@pytest.mark.django_db
def test_product_currency_choices_are_valid():
    valid_codes = {code for code, _ in CURRENCY_CHOICES}
    for code in valid_codes:
        product = _make_product(currency=code)
        product.refresh_from_db()
        assert product.currency == code


@pytest.mark.django_db
def test_product_tax_class_defaults_to_none():
    product = _make_product()
    assert product.tax_class is None


# ---------------------------------------------------------------------------
# TaxClass <-> Product relationship
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_can_be_assigned_a_tax_class():
    tc = _make_tax_class(name="Standard Rate", code="standard")
    product = _make_product(tax_class=tc)
    product.refresh_from_db()
    assert product.tax_class_id == tc.pk
    assert product.tax_class.code == "standard"


@pytest.mark.django_db
def test_multiple_products_can_share_a_tax_class():
    tc = _make_tax_class()
    p1 = _make_product(name="Product A", tax_class=tc)
    p2 = _make_product(name="Product B", tax_class=tc)
    assert tc.products.count() == 2
    assert set(tc.products.values_list("pk", flat=True)) == {p1.pk, p2.pk}


@pytest.mark.django_db
def test_deleting_tax_class_nullifies_product_tax_class():
    tc = _make_tax_class()
    product = _make_product(tax_class=tc)
    tc.delete()
    product.refresh_from_db()
    assert product.tax_class is None


# ---------------------------------------------------------------------------
# Backward compatibility: legacy price field still works
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_product_legacy_price_field_still_works():
    product = _make_product(price=Decimal("49.99"))
    product.refresh_from_db()
    assert product.price == Decimal("49.99")


# ---------------------------------------------------------------------------
# Admin registration smoke-tests
# ---------------------------------------------------------------------------


def test_tax_class_admin_is_registered():
    """TaxClass must be registered with the default admin site."""
    from django.contrib import admin as django_admin

    assert TaxClass in django_admin.site._registry


def test_product_admin_exposes_pricing_fields():
    """ProductAdmin.fields must contain the three pricing foundation fields."""
    site = AdminSite()
    product_admin = ProductAdmin(Product, site)
    assert "price_net_amount" in product_admin.fields
    assert "currency" in product_admin.fields
    assert "tax_class" in product_admin.fields
