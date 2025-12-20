from django.db import models
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=255)
    is_parent = models.BooleanField(default=False)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                name="unique_category_name_per_parent",
            )
        ]

    def clean(self):
        errors = {}

        # Parent category rules
        if self.is_parent and self.parent:
            errors["parent"] = "Parent category cannot have a parent"

        # Leaf category rules
        if not self.is_parent and not self.parent:
            errors["parent"] = "Leaf category must have a parent"

        if self.parent and not self.parent.is_parent:
            errors["parent"] = "Parent must be a parent category"

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name
