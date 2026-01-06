from __future__ import annotations

import os
import json
import random
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Tuple

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import now, timedelta

from products.models import Product
from discounts.models import Discount
from carts.models import Cart, CartItem
from orders.models import Order
from orderitems.models import OrderItem
from payments.models import Payment


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

        self._ensure_superuser()

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
            "users": {},
            "products": {},
            "discounts": {},
            "carts": {},
            "orders": {},
            "payments": {},
        }
        users = data.get("users", []) or []
        products = data.get("products", []) or []
        discounts = data.get("discounts", []) or []
        bulk = data.get("bulk_products", {}) or {}
        carts = data.get("carts", []) or []
        orders = data.get("orders", []) or []
        payments = data.get("payments", []) or []

        user_obj_map, user_fixture_map = self._create_users(users)
        fixtures["users"].update(user_fixture_map)

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

        # Carts (depends on users + products)
        cart_map = self._create_carts(carts, user_obj_map, product_map)
        for key, cart in cart_map.items():
            fixtures["carts"][key] = {
                "id": cart.id,
                "user_id": cart.user_id,
                "status": cart.status,
            }

        # Orders (depends on users + products)
        order_map = self._create_orders(orders, user_obj_map, product_map)
        for key, order in order_map.items():
            fixtures["orders"][key] = {
                "id": order.id,
                "user_id": order.user_id,
                "status": order.status,
            }

        # Payments (depends on orders)
        payment_map = self._create_payments(payments, order_map)
        for key, payment in payment_map.items():
            fixtures["payments"][key] = {
                "id": payment.id,
                "order_id": payment.order_id,
                "status": payment.status,
            }

        return fixtures

    def _create_users(
        self, users: list[dict[str, Any]]
    ) -> Tuple[dict[str, Any], dict[str, dict[str, str]]]:

        User = get_user_model()
        obj_map: dict[str, Any] = {}
        fixture_map: dict[str, dict[str, str]] = {}

        for u in users:
            key = u["key"]
            if not u.get("email"):
                raise ValueError(
                    f"Seed user '{key}' must define 'email' (email-based login is required)."
                )
            email = u["email"]
            password = u.get("password", email)
            first_name = u.get("first_name", "")
            last_name = u.get("last_name", "")

            user, created = User.objects.get_or_create(
                email=email,
                defaults={},
            )
            if created:
                user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                self.stdout.write(f"Created user: {email}")
            else:
                # keep password stable for CI
                user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                self.stdout.write(f"Updated user password: {email}")

            obj_map[key] = user
            fixture_map[key] = {"email": email, "password": password}

        return obj_map, fixture_map

    def _create_carts(
        self,
        carts: list[dict[str, Any]],
        user_obj_map: dict[str, Any],
        product_map: dict[str, Product],
    ) -> dict[str, Cart]:
        out: dict[str, Cart] = {}

        for c in carts:
            key = c["key"]
            user_key = c["user_key"]
            status = c.get("status", Cart.Status.ACTIVE)
            items = c.get("items", []) or []

            if user_key not in user_obj_map:
                raise CommandError(
                    f"Cart {key} references unknown user_key: {user_key}")

            user = user_obj_map[user_key]

            # Create cart (deterministic: always create fresh after reset; update if exists)
            cart, created = Cart.objects.get_or_create(
                user=user,
                status=status,
            )
            if not created:
                # ensure deterministic status
                Cart.objects.filter(id=cart.id).update(status=status)
                cart.refresh_from_db()

            # Clear existing items to keep deterministic
            CartItem.objects.filter(cart=cart).delete()

            for it in items:
                product_key = it["product_key"]
                qty = int(it["quantity"])
                if product_key not in product_map:
                    raise CommandError(
                        f"Cart {key} references unknown product_key: {product_key}")
                product = product_map[product_key]

                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=qty,
                    price_at_add_time=product.price,
                )

            out[key] = cart
            self.stdout.write(
                f"{'Created' if created else 'Updated'} cart: {key} (user={user.username}, status={status})"
            )

        return out

    def _create_orders(
        self,
        orders: list[dict[str, Any]],
        user_obj_map: dict[str, Any],
        product_map: dict[str, Product],
    ) -> dict[str, Order]:
        out: dict[str, Order] = {}

        for o in orders:
            key = o["key"]
            user_key = o.get("user_key")
            status = o.get("status", Order.Status.CREATED)
            items = o.get("items", []) or []

            user = None
            if user_key is not None:
                if user_key not in user_obj_map:
                    raise CommandError(
                        f"Order {key} references unknown user_key: {user_key}")
                user = user_obj_map[user_key]

            order = Order.objects.create(user=user, status=status)

            for it in items:
                product_key = it["product_key"]
                qty = int(it["quantity"])
                if product_key not in product_map:
                    raise CommandError(
                        f"Order {key} references unknown product_key: {product_key}")
                product = product_map[product_key]

                unit = product.price
                line_total = money(unit * qty)

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    # snapshot fields (keep consistent & non-negative)
                    unit_price_at_order_time=unit,
                    line_total_at_order_time=line_total,
                    price_at_order_time=line_total,
                    applied_discount_type_at_order_time=None,
                    applied_discount_value_at_order_time=None,
                )

            out[key] = order
            self.stdout.write(
                f"Created order: {key} (user={getattr(user, 'username', None)}, status={status})"
            )

        return out

    def _create_payments(
        self,
        payments: list[dict[str, Any]],
        order_map: dict[str, Order],
    ) -> dict[str, Payment]:
        out: dict[str, Payment] = {}

        for p in payments:
            key = p["key"]
            order_key = p["order_key"]
            status = p.get("status", Payment.Status.PENDING)

            if order_key not in order_map:
                raise CommandError(
                    f"Payment {key} references unknown order_key: {order_key}")

            order = order_map[order_key]

            if Payment.objects.filter(order=order).exists():
                raise CommandError(
                    f"Payment {key} violates unique_payment_per_order: order_key={order_key}"
                )

            payment = Payment.objects.create(order=order, status=status)
            out[key] = payment
            self.stdout.write(
                f"Created payment: {key} (order={order.id}, status={status})"
            )

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

    def _ensure_superuser(self):
        User = get_user_model()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_staff": True,
                "is_superuser": True,
            },
        )
        # keep credentials deterministic
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{action} superuser: {email}"))
