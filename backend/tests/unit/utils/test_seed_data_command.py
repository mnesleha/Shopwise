from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import override_settings

from categories.models import Category
from discounts.models import AcquisitionMode, Offer, OfferStatus, OrderPromotion, Promotion
from discounts.services.auto_apply_resolver import resolve_auto_apply_order_promotion
from discounts.services.line_promotion import resolve_line_promotion
from products.models import Product, ProductImage, TaxClass
from products.services.pricing import get_product_pricing
from suppliers.models import Supplier, SupplierAddress, SupplierPaymentDetails
from suppliers.services import resolve_order_supplier_snapshot
from utils.seed.common.media import cleanup_demo_product_media
from utils.seed.demo.config import DEMO_PRODUCT_SLUGS
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
    assert headphones.short_description.startswith("Over-ear wireless headphones")
    assert headphones.full_description.startswith("## Wireless Headphones")

    headphones_pricing = get_product_pricing(headphones)
    assert headphones_pricing is not None
    assert headphones_pricing.undiscounted.gross.amount == Decimal("2490.00")
    assert headphones_pricing.undiscounted.net.amount == Decimal("2057.85")

    selected_result = resolve_line_promotion(
        product=headphones,
        net_amount=headphones.price_net_amount,
        currency=headphones.currency,
        tax_rate=headphones.tax_class.rate,
    )
    assert selected_result.promotion is not None
    assert selected_result.promotion.name == "Selected Products 15% Off"

    rope = Product.objects.select_related("category", "tax_class").get(
        slug="chew-toy-rope"
    )
    assert rope.category.name == "Pets"
    assert rope.tax_class.name == "VAT 0%"
    rope_pricing = get_product_pricing(rope)
    assert rope_pricing.undiscounted.gross.amount == Decimal("119.00")
    assert rope_pricing.undiscounted.net.amount == Decimal("119.00")

    keyboard = Product.objects.select_related("category", "tax_class").get(
        slug="mechanical-keyboard"
    )
    category_result = resolve_line_promotion(
        product=keyboard,
        net_amount=keyboard.price_net_amount,
        currency=keyboard.currency,
        tax_rate=keyboard.tax_class.rate,
    )
    assert category_result.promotion is not None
    assert category_result.promotion.name == "Electronics Discount"

    assert Promotion.objects.filter(code="demo-electronics-discount").count() == 1
    assert Promotion.objects.filter(code="demo-selected-products-15-off").count() == 1

    order_promotion = resolve_auto_apply_order_promotion(
        cart_gross=Decimal("4000.00"),
        currency="EUR",
    )
    assert order_promotion is not None
    assert order_promotion.name == "Demo Order Discount"
    assert order_promotion.acquisition_mode == AcquisitionMode.AUTO_APPLY

    campaign_promotion = OrderPromotion.objects.get(code="campaign-welcome-offer")
    assert campaign_promotion.name == "Campaign Welcome Offer"
    assert campaign_promotion.acquisition_mode == AcquisitionMode.CAMPAIGN_APPLY

    offer = Offer.objects.get(token="DEMO-WELCOME-2025")
    assert offer.promotion_id == campaign_promotion.id
    assert offer.status == OfferStatus.DELIVERED
    assert offer.is_currently_active() is True


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
    assert Promotion.objects.filter(code="demo-electronics-discount").count() == 1
    assert Promotion.objects.filter(code="demo-selected-products-15-off").count() == 1
    assert OrderPromotion.objects.filter(code="demo-order-discount").count() == 1
    assert OrderPromotion.objects.filter(code="campaign-welcome-offer").count() == 1
    assert Offer.objects.filter(token="DEMO-WELCOME-2025").count() == 1

    electronics_discount = Promotion.objects.get(code="demo-electronics-discount")
    selected_discount = Promotion.objects.get(code="demo-selected-products-15-off")
    assert electronics_discount.category_targets.count() == 1
    assert electronics_discount.product_targets.count() == 0
    assert selected_discount.category_targets.count() == 0
    assert selected_discount.product_targets.count() == 3

    active_suppliers = Supplier.objects.filter(is_active=True)
    assert active_suppliers.count() == 1
    assert active_suppliers.get().company_id == "SHOPWISE-DEMO-001"


def test_seed_data_demo_reset_replaces_existing_commercial_rows():
    Promotion.objects.create(
        name="Legacy Promo",
        code="legacy-promo",
        type="PERCENT",
        value=Decimal("5.00"),
        is_active=True,
    )
    legacy_order_promotion = OrderPromotion.objects.create(
        name="Legacy Order Promo",
        code="legacy-order-promo",
        type="FIXED",
        value=Decimal("100.00"),
        acquisition_mode=AcquisitionMode.AUTO_APPLY,
        is_active=True,
    )
    Offer.objects.create(
        token="LEGACY-TOKEN",
        promotion=legacy_order_promotion,
        status=OfferStatus.CREATED,
        is_active=True,
    )

    call_command("seed_data", profile="demo", reset=True)

    assert Promotion.objects.filter(code="legacy-promo").exists() is False
    assert OrderPromotion.objects.filter(code="legacy-order-promo").exists() is False
    assert Offer.objects.filter(token="LEGACY-TOKEN").exists() is False
    assert Offer.objects.filter(token="DEMO-WELCOME-2025").count() == 1


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


@override_settings(MEDIA_ROOT="test-media-root")
def test_cleanup_demo_product_media_deletes_only_demo_linked_media(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"

    demo_product = Product.objects.create(
        name="Demo Product",
        slug="wireless-headphones",
        price=Decimal("10.00"),
        stock_quantity=10,
        is_active=True,
    )
    demo_image = _create_product_image(demo_product, "demo-image.jpg")
    demo_product.primary_image = demo_image
    demo_product.save(update_fields=["primary_image"])

    other_product = Product.objects.create(
        name="Other Product",
        slug="non-demo-product",
        price=Decimal("11.00"),
        stock_quantity=10,
        is_active=True,
    )
    other_image = _create_product_image(other_product, "other-image.jpg")
    other_product.primary_image = other_image
    other_product.save(update_fields=["primary_image"])

    demo_file_name = demo_image.image.name
    other_file_name = other_image.image.name

    cleanup_demo_product_media(product_slugs=DEMO_PRODUCT_SLUGS)

    demo_product.refresh_from_db()
    other_product.refresh_from_db()

    assert demo_product.primary_image_id is None
    assert demo_product.images.count() == 0
    assert demo_image.image.storage.exists(demo_file_name) is False

    assert other_product.primary_image_id == other_image.id
    assert other_product.images.count() == 1
    assert other_image.image.storage.exists(other_file_name) is True


@override_settings(MEDIA_ROOT="test-media-root")
def test_cleanup_demo_product_media_removes_empty_local_directory(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"

    demo_product = Product.objects.create(
        name="Demo Product",
        slug="wireless-headphones",
        price=Decimal("10.00"),
        stock_quantity=10,
        is_active=True,
    )
    demo_image = _create_product_image(demo_product, "demo-image.jpg")
    image_directory = Path(demo_image.image.storage.path(demo_image.image.name)).parent

    assert image_directory.exists() is True

    cleanup_demo_product_media(product_slugs=DEMO_PRODUCT_SLUGS)

    assert image_directory.exists() is False


@override_settings(MEDIA_ROOT="test-media-root")
def test_cleanup_demo_product_media_tolerates_missing_files_and_dirs(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"

    demo_product = Product.objects.create(
        name="Demo Product",
        slug="wireless-headphones",
        price=Decimal("10.00"),
        stock_quantity=10,
        is_active=True,
    )
    demo_image = _create_product_image(demo_product, "demo-image.jpg")
    image_path = Path(demo_image.image.storage.path(demo_image.image.name))
    image_directory = image_path.parent
    image_path.unlink()
    image_directory.rmdir()

    cleanup_demo_product_media(product_slugs=DEMO_PRODUCT_SLUGS)

    demo_product.refresh_from_db()
    assert demo_product.primary_image_id is None
    assert demo_product.images.count() == 0


def _create_product_image(product: Product, filename: str) -> ProductImage:
    image = ProductImage(product=product, alt_text=product.name, sort_order=0)
    image.image.save(filename, ContentFile(TINY_JPEG), save=False)
    image.save()
    return image