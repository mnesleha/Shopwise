from django.db import models
from django.db import IntegrityError
from django.db.models import UniqueConstraint, Q
from django.conf import settings
from products.models import Product
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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

    def clean(self):
        """
        Enforce Cart domain invariants.

        Notes:
        - Validation must live in clean() so that full_clean() (and unit tests) catches issues.
        - save() calls full_clean() to ensure invariants are enforced for all persistence paths.
        """
        super().clean()

        # Invariant: a user can have only one ACTIVE cart (applies only when user is set).
        if self.status == Cart.Status.ACTIVE:
            if self.user and Cart.objects.filter(
                user=self.user,
                status=Cart.Status.ACTIVE,
            ).exclude(pk=self.pk).exists():
                raise ValidationError("User already has an active cart.")

        # MERGED invariant enforcement
        if self.status == Cart.Status.MERGED:
            if self.anonymous_token_hash is not None:
                raise ValidationError({
                    "anonymous_token_hash": _("MERGED carts must not have a token hash.")
                })
            if self.merged_into_cart is None:
                raise ValidationError({
                    "merged_into_cart": _("MERGED carts must reference the target user cart.")
                })
            if self.merged_at is None:
                raise ValidationError({
                    "merged_at": _("MERGED carts must have merged_at set.")
                })
            return

        # Non-MERGED carts must not carry merge metadata.
        if self.merged_into_cart is not None:
            raise ValidationError({
                "merged_into_cart": _("Only MERGED carts may reference merged_into_cart.")
            })
        if self.merged_at is not None:
            raise ValidationError({
                "merged_at": _("Only MERGED carts may have merged_at set.")
            })

    def save(self, *args, **kwargs):
        # Enforce invariants + unique validation at model level (tests expect ValidationError)
        self.full_clean()
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["cart", "product"],
                             name="cart_item_cart_product_uniq"),
        ]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ActiveCart(models.Model):
    """
    Pointer table enforcing a single current ACTIVE cart per authenticated user.
    MySQL-safe replacement for partial unique constraints.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="active_cart_ptr",
    )
    cart = models.ForeignKey(
        "Cart",
        on_delete=models.CASCADE,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["cart"]),
        ]
