from __future__ import annotations

import json
import random
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import now, timedelta

from products.models import Product
from discounts.models import Discount


MONEY_Q = Decimal("0.01")


def money(val: Any) -> Decimal:
    """
    Parse a numeric-ish value to Decimal with 2dp, HALF_UP.
    Accepts str/Decimal/int/float (float discouraged).
    """
    d = Decimal(str(val))
    return d.quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def safe_get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def safe_delete_all(app_label: str, model_name: str) -> int:
    model = safe_get_model(app_label, model_name)
    if model is None:
        return 0
    deleted, _ = model.objects.all().delete()
    return deleted


@dataclass(frozen=True)
class SeedPaths:
    backend_root: Path
    seed_dir: Path

    @staticmethod
    def from_command_file(command_file: Path) -> "SeedPaths":
        # backend/utils/management/commands/seed_test_data.py
        backend_root = command_file.resolve().parents[3]
        seed_dir = backend_root / "utils" / "seed"
        return SeedPaths(backend_root=backend_root, seed_dir=seed_dir)


class Command(BaseCommand):
    help = "Seed deterministic E2E test data for local dev, Postman, and CI."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            default="e2e",
            help="Seed profile name (loads backend/utils/seed/<profile>.yaml). Default: e2e",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing data from relevant tables before seeding.",
        )
        parser.add_argument(
            "--export-fixtures",
            default=None,
            help="Write a fixtures JSON map (keys -> created IDs + user creds) to this path.",
        )

    def handle(self, *args, **options):
        profile: str = options["profile"]
        reset: bool = options["reset"]
        export_path: str | None = options["export_fixtures"]

        paths = SeedPaths.from_command_file(Path(__file__))
        yaml_path = paths.seed_dir / f"{profile}.yaml"

        if not yaml_path.exists():
            raise CommandError(
                f"Seed profile not found: {yaml_path}. Create it (e.g. backend/utils/seed/e2e.yaml)."
            )

        try:
            import yaml  # type: ignore
        except Exception as e:
            raise CommandError(
                "PyYAML is required for YAML-driven seed. Install it: pip install pyyaml"
            ) from e

        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if reset:
            self._reset_db()

        # Everything should be deterministic and atomic.
        with transaction.atomic():
            fixtures = self._seed_from_yaml(data)

        if export_path:
            out = Path(export_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(fixtures, indent=2,
                           ensure_ascii=False), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(
                f"Exported fixtures -> {out}"))

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    # -----------------------
    # Reset
    # -----------------------
    def _reset_db(self):
        self.stdout.write("Resetting relevant tables...")

        # Domain runtime data
        safe_delete_all("payments", "Payment")
        safe_delete_all("orderitems", "OrderItem")
        safe_delete_all("orders", "Order")
        safe_delete_all("carts", "CartItem")
        safe_delete_all("carts", "Cart")

        # Reference data (in correct dependency order)
        Discount.objects.all().delete()
        Product.objects.all().delete()

        # Users are usually fine to keep, but for deterministic CI you may want to wipe them too.
        # We'll keep them by default; seed uses get_or_create.
        self.stdout.write(self.style.SUCCESS("Reset done."))

    # -----------------------
    # Seed
    # -----------------------
    def _seed_from_yaml(self, data: dict[str, Any]) -> dict[str, Any]:
        fixtures: dict[str, Any] = {
            "users": {}, "products": {}, "discounts": {}}

        users = data.get("users", []) or []
        products = data.get("products", []) or []
        discounts = data.get("discounts", []) or {}
        bulk = data.get("bulk_products", {}) or {}

        user_map = self._create_users(users)
        for k, v in user_map.items():
            fixtures["users"][k] = v

        product_map = self._create_products(products)
        for key, product in product_map.items():
            fixtures["products"][key] = {
                "id": product.id, "name": product.name}

        # Bulk products (optional)
        if bulk.get("enabled"):
            bulk_created = self._create_bulk_products(bulk)
            fixtures["products"]["__bulk__"] = {"count": bulk_created}

        discount_map = self._create_discounts(discounts, product_map)
        for key, discount in discount_map.items():
            fixtures["discounts"][key] = {
                "id": discount.id, "name": discount.name}

        return fixtures

    def _create_users(self, users: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
        User = get_user_model()
        out: dict[str, dict[str, str]] = {}

        for u in users:
            key = u["key"]
            username = u["username"]
            password = u.get("password", username)

            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"Created user: {username}")
            else:
                # keep password stable for CI
                user.set_password(password)
                user.save()
                self.stdout.write(f"Updated user password: {username}")

            out[key] = {"username": username, "password": password}

        return out

    def _create_products(self, products: list[dict[str, Any]]) -> dict[str, Product]:
        out: dict[str, Product] = {}

        for p in products:
            key = p["key"]
            name = p["name"]

            defaults = {
                "price": money(p["price"]),
                "stock_quantity": int(p["stock_quantity"]),
                "is_active": bool(p["is_active"]),
            }

            product, created = Product.objects.get_or_create(
                name=name, defaults=defaults)
            if not created:
                # keep deterministic updates
                Product.objects.filter(id=product.id).update(**defaults)
                product.refresh_from_db()

            out[key] = product
            self.stdout.write(
                f"{'Created' if created else 'Updated'} product: {name} (key={key})")

        return out

    def _create_bulk_products(self, bulk: dict[str, Any]) -> int:
        count = int(bulk.get("count", 0))
        prefix = str(bulk.get("name_prefix", "E2E_BULK_"))
        seed = int(bulk.get("deterministic_seed", 12345))

        price_min = money(bulk.get("price_min", "5.00"))
        price_max = money(bulk.get("price_max", "500.00"))
        stock_min = int(bulk.get("stock_min", 0))
        stock_max = int(bulk.get("stock_max", 50))
        active_ratio = float(bulk.get("active_ratio", 0.9))

        rng = random.Random(seed)

        created = 0
        for i in range(1, count + 1):
            name = f"{prefix}{i:04d}"

            # deterministic pseudo-random generation
            price = money(price_min + (price_max - price_min)
                          * Decimal(str(rng.random())))
            stock = rng.randint(stock_min, stock_max)
            is_active = rng.random() < active_ratio

            _, was_created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "price": price,
                    "stock_quantity": stock,
                    "is_active": is_active,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(f"Bulk products created: {created}/{count}")
        return created

    def _create_discounts(
        self, discounts: list[dict[str, Any]], product_map: dict[str, Product]
    ) -> dict[str, Discount]:
        out: dict[str, Discount] = {}
        today = now().date()

        for d in discounts:
            key = d["key"]
            name = d["name"]
            discount_type = d["discount_type"]
            value = money(d["value"])
            is_active = bool(d.get("is_active", True))

            product_key = d.get("product_key")
            if not product_key:
                raise CommandError(f"Discount {key} missing product_key")
            if product_key not in product_map:
                raise CommandError(
                    f"Discount {key} references unknown product_key: {product_key}")

            valid_from = today + \
                timedelta(days=int(d.get("valid_from_offset_days", -1)))
            valid_to = today + \
                timedelta(days=int(d.get("valid_to_offset_days", 5)))

            defaults = {
                "discount_type": discount_type,
                "value": value,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "is_active": is_active,
                "product": product_map[product_key],
            }

            disc, created = Discount.objects.get_or_create(
                name=name, defaults=defaults)
            if not created:
                Discount.objects.filter(id=disc.id).update(**defaults)
                disc.refresh_from_db()

            out[key] = disc
            self.stdout.write(
                f"{'Created' if created else 'Updated'} discount: {name} (key={key})")

        return out
