from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from categories.models import Category
from products.models import Product, TaxClass
from suppliers.models import Supplier, SupplierAddress, SupplierPaymentDetails

from utils.seed.common.export import write_fixture_export
from utils.seed.common.media import (
    cleanup_demo_product_media,
    get_demo_product_asset_files,
    sync_product_media,
)
from utils.seed.common.reset import reset_demo_seed_data
from utils.seed.demo.commercial import seed_demo_commercial_layer
from utils.seed.demo.config import (
    DEMO_CATEGORIES,
    DEMO_PRODUCTS,
    DEMO_PRODUCT_SLUGS,
    DEMO_SUPPLIER,
    DEMO_TAX_CLASSES,
    DEMO_USERS,
)


WriteLine = Callable[[str], None]
MONEY_QUANTIZE = Decimal("0.01")
HUNDRED = Decimal("100")


def run_demo_seed(
    *,
    reset: bool = False,
    export_path: str | None = None,
    asset_root: str | Path | None = None,
    write_line: WriteLine | None = None,
) -> None:
    write = write_line or (lambda message: None)

    if reset:
        cleanup_demo_product_media(product_slugs=DEMO_PRODUCT_SLUGS, write_line=write)
        reset_demo_seed_data(write)

    with transaction.atomic():
        fixtures = {
            "users": _seed_users(write),
            "tax_classes": _seed_tax_classes(write),
            "supplier": _seed_supplier(write),
            "categories": _seed_categories(write),
            "products": _seed_products(write),
            "commercial": seed_demo_commercial_layer(write),
            "media": _seed_product_media(write, asset_root=asset_root),
        }

    if export_path:
        output_path = write_fixture_export(export_path, fixtures)
        write(f"Exported fixtures -> {output_path}")


def _seed_users(write: WriteLine) -> dict[str, dict[str, Any]]:
    user_model = get_user_model()
    fixtures: dict[str, dict[str, Any]] = {}

    for user_data in DEMO_USERS:
        email = user_data["email"].strip().lower()
        password = user_data["password"]
        is_superuser = bool(user_data["is_superuser"])
        is_staff = bool(user_data["is_staff"])

        user = user_model.objects.filter(email=email).first()
        created = user is None

        if created:
            create_method = (
                user_model.objects.create_superuser
                if is_superuser
                else user_model.objects.create_user
            )
            user = create_method(
                email=email,
                password=password,
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                is_staff=is_staff,
                email_verified=bool(user_data.get("email_verified", False)),
            )
        else:
            user.first_name = user_data["first_name"]
            user.last_name = user_data["last_name"]
            user.is_active = True
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.email_verified = bool(user_data.get("email_verified", False))
            user.set_password(password)
            user.save()

        fixtures[user_data["key"]] = {
            "id": user.id,
            "email": email,
            "password": password,
        }
        write(f"{'Created' if created else 'Updated'} demo user: {email}")

    return fixtures


def _seed_tax_classes(write: WriteLine) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}

    for tax_class_data in DEMO_TAX_CLASSES:
        tax_class, created = TaxClass.objects.update_or_create(
            code=tax_class_data["code"],
            defaults={
                "name": tax_class_data["name"],
                "description": tax_class_data["description"],
                "rate": Decimal(tax_class_data["rate"]),
                "is_active": True,
            },
        )
        fixtures[tax_class_data["key"]] = {
            "id": tax_class.id,
            "code": tax_class.code,
        }
        write(
            f"{'Created' if created else 'Updated'} tax class: {tax_class.name}"
        )

    return fixtures


def _seed_supplier(write: WriteLine) -> dict[str, Any]:
    lookup = DEMO_SUPPLIER["lookup"]
    defaults = DEMO_SUPPLIER["defaults"]

    Supplier.objects.exclude(**lookup).update(is_active=False)
    supplier, created = Supplier.objects.update_or_create(
        **lookup,
        defaults=defaults,
    )

    address_fixtures: dict[str, dict[str, Any]] = {}
    kept_address_ids: list[int] = []
    for address_data in DEMO_SUPPLIER["addresses"]:
        address, _ = SupplierAddress.objects.update_or_create(
            supplier=supplier,
            label=address_data["label"],
            defaults={
                "street_line_1": address_data["street_line_1"],
                "street_line_2": address_data["street_line_2"],
                "city": address_data["city"],
                "postal_code": address_data["postal_code"],
                "country": address_data["country"],
                "is_default_for_orders": address_data["is_default_for_orders"],
            },
        )
        kept_address_ids.append(address.id)
        address_fixtures[address_data["key"]] = {"id": address.id}

    SupplierAddress.objects.filter(supplier=supplier).exclude(
        id__in=kept_address_ids
    ).delete()

    payment_fixtures: dict[str, dict[str, Any]] = {}
    kept_payment_ids: list[int] = []
    for payment_data in DEMO_SUPPLIER["payment_details"]:
        payment_details, _ = SupplierPaymentDetails.objects.update_or_create(
            supplier=supplier,
            label=payment_data["label"],
            defaults={
                "bank_name": payment_data["bank_name"],
                "account_number": payment_data["account_number"],
                "iban": payment_data["iban"],
                "swift": payment_data["swift"],
                "is_default_for_orders": payment_data["is_default_for_orders"],
            },
        )
        kept_payment_ids.append(payment_details.id)
        payment_fixtures[payment_data["key"]] = {"id": payment_details.id}

    SupplierPaymentDetails.objects.filter(supplier=supplier).exclude(
        id__in=kept_payment_ids
    ).delete()

    write(f"{'Created' if created else 'Updated'} demo supplier: {supplier.name}")

    return {
        "id": supplier.id,
        "name": supplier.name,
        "addresses": address_fixtures,
        "payment_details": payment_fixtures,
    }


def _seed_categories(write: WriteLine) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}

    for category_data in DEMO_CATEGORIES:
        category, created = Category.objects.update_or_create(
            name=category_data["name"],
            defaults={},
        )
        fixtures[category_data["key"]] = {
            "id": category.id,
            "name": category.name,
        }
        write(f"{'Created' if created else 'Updated'} category: {category.name}")

    return fixtures


def _seed_products(write: WriteLine) -> dict[str, dict[str, Any]]:
    category_map = {category.name: category for category in Category.objects.all()}
    tax_class_map = {tax_class.name: tax_class for tax_class in TaxClass.objects.all()}
    fixtures: dict[str, dict[str, Any]] = {}

    for product_data in DEMO_PRODUCTS:
        category = category_map[product_data["category_name"]]
        tax_class = tax_class_map[product_data["tax_class_name"]]
        gross_price = Decimal(product_data["price"])
        net_price = _net_amount_from_gross(gross_price, tax_class.rate)

        product, created = Product.objects.update_or_create(
            slug=product_data["slug"],
            defaults={
                "name": product_data["name"],
                "price": gross_price,
                "price_net_amount": net_price,
                "currency": "EUR",
                "tax_class": tax_class,
                "stock_quantity": product_data["stock_quantity"],
                "is_active": True,
                "category": category,
                "short_description": product_data["short_description"],
                "full_description": product_data["full_description"],
            },
        )

        fixtures[product_data["key"]] = {
            "id": product.id,
            "slug": product.slug,
            "price": str(product.price),
        }
        write(f"{'Created' if created else 'Updated'} product: {product.name}")

    return fixtures


def _seed_product_media(
    write: WriteLine,
    *,
    asset_root: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}
    products = Product.objects.all().order_by("name")

    for product in products:
        asset_files = get_demo_product_asset_files(
            slug=product.slug,
            assets_root=asset_root,
        )
        synced_images = sync_product_media(
            product=product,
            asset_files=asset_files,
            write_line=write,
        )
        fixtures[product.slug] = {
            "count": len(synced_images),
            "primary_image_id": product.primary_image_id,
        }

    return fixtures


def _net_amount_from_gross(gross_amount: Decimal, tax_rate: Decimal | None) -> Decimal:
    if tax_rate is None or tax_rate == 0:
        return gross_amount.quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)

    divisor = Decimal("1") + (tax_rate / HUNDRED)
    return (gross_amount / divisor).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)