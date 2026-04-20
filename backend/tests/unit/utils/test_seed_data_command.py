from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from categories.models import Category
from products.models import TaxClass
from suppliers.models import Supplier, SupplierAddress, SupplierPaymentDetails
from suppliers.services import resolve_order_supplier_snapshot


pytestmark = pytest.mark.django_db


def test_seed_data_demo_creates_phase_1_reference_data():
    call_command("seed_data", profile="demo", reset=True)

    user_model = get_user_model()
    superuser = user_model.objects.get(email="admin@shopwise.test")
    staff = user_model.objects.get(email="staff@shopwise.test")
    customer_1 = user_model.objects.get(email="alice.walker@shopwise.test")
    customer_2 = user_model.objects.get(email="martin.novak@shopwise.test")

    assert superuser.is_superuser is True
    assert superuser.is_staff is True
    assert staff.is_staff is True
    assert staff.is_superuser is False
    assert customer_1.is_staff is False
    assert customer_2.is_superuser is False

    assert TaxClass.objects.filter(code="vat-21", rate=Decimal("21.0000")).exists()
    assert TaxClass.objects.filter(code="vat-12", rate=Decimal("12.0000")).exists()
    assert TaxClass.objects.filter(code="vat-0", rate=Decimal("0.0000")).exists()

    supplier = Supplier.objects.get(company_id="SHOPWISE-DEMO-001")
    assert supplier.is_active is True
    assert SupplierAddress.objects.filter(
        supplier=supplier,
        is_default_for_orders=True,
    ).count() == 1
    assert SupplierPaymentDetails.objects.filter(
        supplier=supplier,
        is_default_for_orders=True,
    ).count() == 1

    snapshot = resolve_order_supplier_snapshot()
    assert snapshot.name == supplier.name
    assert snapshot.iban == "CZ6508000000001234567899"

    assert set(Category.objects.values_list("name", flat=True)) == {
        "Electronics",
        "Grocery",
        "Pets",
    }


def test_seed_data_demo_is_repeatable_and_normalizes_active_supplier():
    other_supplier = Supplier.objects.create(name="Legacy Supplier", company_id="LEGACY-1", is_active=True)
    SupplierAddress.objects.create(
        supplier=other_supplier,
        label="Legacy",
        street_line_1="Old Street 1",
        city="Prague",
        postal_code="11000",
        country="CZ",
        is_default_for_orders=True,
    )
    SupplierPaymentDetails.objects.create(
        supplier=other_supplier,
        label="Legacy Account",
        iban="CZ0000000000000000000001",
        is_default_for_orders=True,
    )

    call_command("seed_data", profile="demo")
    call_command("seed_data", profile="demo")

    assert get_user_model().objects.filter(email="admin@shopwise.test").count() == 1
    assert TaxClass.objects.filter(code="vat-21").count() == 1
    assert Category.objects.filter(name="Electronics").count() == 1

    active_suppliers = Supplier.objects.filter(is_active=True)
    assert active_suppliers.count() == 1
    assert active_suppliers.get().company_id == "SHOPWISE-DEMO-001"


def test_seed_data_dev_delegates_to_legacy_seed_command(monkeypatch):
    captured: dict[str, object] = {}

    def fake_call_command(command_name, *args, **kwargs):
        captured["command_name"] = command_name
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr("utils.seed.dev.seed.call_command", fake_call_command)

    call_command(
        "seed_data",
        profile="dev",
        reset=True,
        export_fixtures="fixtures/dev-seed.json",
    )

    assert captured["command_name"] == "seed_test_data"
    assert captured["kwargs"] == {
        "profile": "e2e",
        "reset": True,
        "export_fixtures": "fixtures/dev-seed.json",
    }