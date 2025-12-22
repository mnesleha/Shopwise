from django.db import models
from django.contrib.auth.models import User
from products.models import Product
from django.core.exceptions import ValidationError


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        CONVERTED = "CONVERTED"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name="items",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_add_time = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
