from django.db import models
from django.conf import settings
from products.models import Product
from django.core.exceptions import ValidationError


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        CONVERTED = "CONVERTED"
        MERGED = "MERGED"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
        null=True,
        blank=True,
    )
    anonymous_token_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    merged_into_cart = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="merged_carts",
        null=True,
        blank=True,
    )
    merged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.status == Cart.Status.ACTIVE:
            if self.user and Cart.objects.filter(
                user=self.user,
                status=Cart.Status.ACTIVE,
            ).exclude(pk=self.pk).exists():
                raise ValidationError("User already has an active cart.")
        if self.status == Cart.Status.MERGED:
            if self.anonymous_token_hash is not None:
                raise ValidationError("Merged carts cannot be addressable by token.")
            if self.merged_into_cart is None or self.merged_at is None:
                raise ValidationError("Merged carts must have merge metadata.")
        else:
            if self.merged_into_cart_id or self.merged_at:
                self.merged_into_cart = None
                self.merged_at = None
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
