from django.db import models
from django.conf import settings
from products.models import Product
from django.core.exceptions import ValidationError


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        CONVERTED = "CONVERTED"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.status == Cart.Status.ACTIVE:
            if Cart.objects.filter(
                user=self.user,
                status=Cart.Status.ACTIVE
            ).exclude(pk=self.pk).exists():
                raise ValidationError("User already has an active cart.")
        super().save(*args, **kwargs)


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
