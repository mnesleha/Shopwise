from django.db import models
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    def clean(self):
        errors = {}

        # 1️⃣ Name validation
        if not self.name:
            errors["name"] = "Category name cannot be empty"

        # 2️⃣ Self-parent validation (ALWAYS)
        if self.parent is not None and self.parent is self:
            errors["parent"] = "Category cannot be its own parent"

        # 3️⃣ Cycle detection (in-memory safe)
        seen = set()
        ancestor = self.parent

        while ancestor is not None:
            if ancestor is self:
                errors["parent"] = "Category hierarchy cannot contain cycles"
                break
            if ancestor in seen:
                break
            seen.add(ancestor)
            ancestor = ancestor.parent

        # 4️⃣ Uniqueness within same parent
        # This validation is enforced at application level
        # and intentionally works even for unsaved instances.
        if self.parent:
            siblings = self.parent.children.all() if self.parent.pk else []
        else:
            siblings = Category.objects.filter(
                parent__isnull=True) if self.pk else []

        for sibling in siblings:
            if sibling is not self and sibling.name == self.name:
                errors["name"] = "Category name must be unique within the same parent"
                break

        if errors:
            raise ValidationError(errors)
