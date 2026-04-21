from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings

from categories.models import Category
from products.models import Product, ProductImage, TaxClass
from products.services.pricing import get_product_pricing
from suppliers.models import Supplier, SupplierAddress, SupplierPaymentDetails
from suppliers.services import resolve_order_supplier_snapshot
from utils.seed.demo.seed import run_demo_seed


pytestmark = pytest.mark.django_db

TINY_JPEG = b"\xff\xd8\xff\xdb\x00C\x00" + b"\x08" * 64 + b"\xff\xd9"


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

    assert Product.objects.count() == 15

    headphones = Product.objects.select_related("category", "tax_class").get(
        slug="wireless-headphones"
    )
    assert headphones.name == "Wireless Headphones"
    assert headphones.category.name == "Electronics"
    assert headphones.tax_class.name == "VAT 21%"
    assert headphones.stock_quantity == 50
    assert headphones.is_active is True
    assert headphones.price == Decimal("2490.00")

    headphones_pricing = get_product_pricing(headphones)
    assert headphones_pricing is not None
    assert headphones_pricing.undiscounted.gross.amount == Decimal("2490.00")
    assert headphones_pricing.undiscounted.net.amount == Decimal("2057.85")

    rope = Product.objects.select_related("category", "tax_class").get(
        slug="chew-toy-rope"
    )
    assert rope.category.name == "Pets"
    assert rope.tax_class.name == "VAT 0%"
    rope_pricing = get_product_pricing(rope)
    assert rope_pricing.undiscounted.gross.amount == Decimal("119.00")
    assert rope_pricing.undiscounted.net.amount == Decimal("119.00")


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
    assert Product.objects.filter(slug="wireless-headphones").count() == 1
    assert Product.objects.count() == 15

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


@override_settings(MEDIA_ROOT="test-media-root")
def test_demo_seed_syncs_media_from_slug_asset_folders(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    asset_root = tmp_path / "assets" / "products"
    _write_asset(asset_root, "wireless-headphones", "wireless-headphones-1.jpg")
    _write_asset(asset_root, "wireless-headphones", "wireless-headphones-2.jpg")
    _write_asset(asset_root, "green-tea", "green-tea-1.jpg")

    run_demo_seed(reset=True, asset_root=asset_root)

    headphones = Product.objects.get(slug="wireless-headphones")
    green_tea = Product.objects.get(slug="green-tea")

    headphone_images = list(headphones.images.all())
    assert len(headphone_images) == 2
    assert headphones.primary_image_id == headphone_images[0].id
    assert headphone_images[0].sort_order == 0
    assert headphone_images[1].sort_order == 1
    assert Path(headphone_images[0].image.name).name == "wireless-headphones-1.jpg"
    assert Path(headphone_images[1].image.name).name == "wireless-headphones-2.jpg"
    assert headphone_images[0].image.storage.exists(headphone_images[0].image.name)

    tea_images = list(green_tea.images.all())
    assert len(tea_images) == 1
    assert green_tea.primary_image_id == tea_images[0].id
    assert Path(tea_images[0].image.name).name == "green-tea-1.jpg"


@override_settings(MEDIA_ROOT="test-media-root")
def test_demo_seed_media_rerun_replaces_gallery_deterministically(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    asset_root = tmp_path / "assets" / "products"
    product_slug = "wireless-headphones"

    _write_asset(asset_root, product_slug, f"{product_slug}-1.jpg")
    _write_asset(asset_root, product_slug, f"{product_slug}-2.jpg")
    _write_asset(asset_root, product_slug, f"{product_slug}-3.jpg")

    run_demo_seed(reset=True, asset_root=asset_root)

    product = Product.objects.get(slug=product_slug)
    assert product.images.count() == 3

    (asset_root / product_slug / f"{product_slug}-3.jpg").unlink()
    _write_asset(asset_root, product_slug, f"{product_slug}-4.jpg")

    run_demo_seed(asset_root=asset_root)

    product.refresh_from_db()
    images = list(product.images.all())
    assert len(images) == 3
    assert product.primary_image_id == images[0].id
    assert [Path(image.image.name).name for image in images] == [
        f"{product_slug}-1.jpg",
        f"{product_slug}-2.jpg",
        f"{product_slug}-4.jpg",
    ]
    assert ProductImage.objects.filter(product=product).count() == 3


def _write_asset(asset_root: Path, slug: str, filename: str) -> None:
    product_dir = asset_root / slug
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / filename).write_bytes(TINY_JPEG)