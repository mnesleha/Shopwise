from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal

from products.models import Product
from discounts.models import Discount
from django.utils.timezone import now, timedelta


class Command(BaseCommand):
    help = "Seed minimal test data for local development and QA testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset runtime data (carts, orders, payments) before seeding",
        )

    def handle(self, *args, **options):
        self.stdout.write("Seeding test data...")

        if options["reset"]:
            self.reset_runtime_data()

        self.create_users()
        self.create_products()
        self.create_discounts()

        self.stdout.write(self.style.SUCCESS("Test data seeded successfully."))

    def reset_runtime_data(self):
        from carts.models import CartItem, Cart
        from orders.models import Order
        from orderitems.models import OrderItem
        from payments.models import Payment

        self.stdout.write("Resetting runtime data...")

        CartItem.objects.all().delete()
        Cart.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        Payment.objects.all().delete()

        self.stdout.write(self.style.WARNING("Runtime data reset completed."))

    def create_users(self):
        User = get_user_model()

        usernames = [
            "karenblack",
            "paulrabbit",
            "alicebrown",
            "bobsmith",
            "jimwhite",
            "carolgreen",
        ]

        for username in usernames:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={},
            )

            if created:
                user.set_password(username)
                user.save()
                self.stdout.write(f"Created user: {username}")
            else:
                self.stdout.write(f"User already exists: {username}")

    def create_products(self):
        products = [
            {
                "name": "Sellable Mouse",
                "price": Decimal("100.00"),
                "stock_quantity": 10,
                "is_active": True,
            },
            {
                "name": "Out of Stock Mouse",
                "price": Decimal("50.00"),
                "stock_quantity": 0,
                "is_active": True,
            },
            {
                "name": "Inactive Mouse",
                "price": Decimal("30.00"),
                "stock_quantity": 10,
                "is_active": False,
            },
        ]

        for data in products:
            product, created = Product.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )

            if created:
                self.stdout.write(f"Created product: {product.name}")
            else:
                self.stdout.write(f"Product already exists: {product.name}")

    def create_discounts(self):
        product = Product.objects.filter(name="Sellable Product").first()
        if not product:
            self.stdout.write("No product for discounts, skipping.")
            return

    def create_discounts(self):
        product = Product.objects.filter(name="Sellable Mouse").first()
        if not product:
            self.stdout.write("No product for discounts, skipping.")
            return

        discounts = [
            # PERCENT
            {
                "name": "Active Percent Discount",
                "discount_type": Discount.PERCENT,
                "value": Decimal("10.00"),
                "valid_from": now().date() - timedelta(days=1),
                "valid_to": now().date() + timedelta(days=5),
                "is_active": True,
                "product": product,
            },
            {
                "name": "Expired Percent Discount",
                "discount_type": Discount.PERCENT,
                "value": Decimal("20.00"),
                "valid_from": now().date() - timedelta(days=10),
                "valid_to": now().date() - timedelta(days=5),
                "is_active": True,
                "product": product,
            },

            # FIXED – EDGE CASES
            {
                "name": "Active Fixed Discount",
                "discount_type": Discount.FIXED,
                "value": Decimal("150.00"),  # > product price
                "valid_from": now().date() - timedelta(days=1),
                "valid_to": now().date() + timedelta(days=5),
                "is_active": True,
                "product": product,
            },
            {
                "name": "Inactive Fixed Discount",
                "discount_type": Discount.FIXED,
                "value": Decimal("20.00"),
                "valid_from": now().date() - timedelta(days=1),
                "valid_to": now().date() + timedelta(days=5),
                "is_active": False,
                "product": product,
            },
        ]

        for data in discounts:
            discount, created = Discount.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )

            if created:
                self.stdout.write(f"Created discount: {discount.name}")
            else:
                self.stdout.write(f"Discount already exists: {discount.name}")
