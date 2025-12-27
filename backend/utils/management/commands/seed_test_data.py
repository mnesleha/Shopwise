from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal

from products.models import Product
from discounts.models import Discount
from django.utils.timezone import now, timedelta


class Command(BaseCommand):
    help = "Seed minimal test data for local development and QA testing"

    def handle(self, *args, **options):
        self.stdout.write("Seeding test data...")

        self.create_users()
        self.create_products()
        self.create_discounts()

        self.stdout.write(self.style.SUCCESS("Test data seeded successfully."))

    def create_users(self):
        User = get_user_model()

        users = [
            {
                "username": "tomjohnes",
                "password": "tomjohnes",
            },
            {
                "username": "frankmills",
                "password": "frankmills",
            },
        ]

        for user_data in users:
            user, created = User.objects.get_or_create(
                username=user_data["username"],
                defaults={},
            )

            if created:
                user.set_password(user_data["password"])
                user.save()
                self.stdout.write(f"Created user: {user.username}")
            else:
                self.stdout.write(f"User already exists: {user.username}")

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

        discounts = [
            {
                "name": "Active Mouse Discount",
                "discount_type": Discount.PERCENT,
                "value": Decimal("10.00"),
                "valid_from": now().date() - timedelta(days=1),
                "valid_to": now().date() + timedelta(days=5),
                "is_active": True,
                "product": product,
            },
            {
                "name": "Expired Mouse Discount",
                "discount_type": Discount.PERCENT,
                "value": Decimal("20.00"),
                "valid_from": now().date() - timedelta(days=10),
                "valid_to": now().date() - timedelta(days=5),
                "is_active": True,
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
