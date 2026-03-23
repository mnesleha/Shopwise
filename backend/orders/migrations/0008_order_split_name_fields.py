"""
Migration 0008: split shipping_name → shipping_first_name + shipping_last_name
                       billing_name  → billing_first_name  + billing_last_name

Strategy
--------
1. Add new fields (shipping_first_name / last_name with empty-string default so
   existing rows remain constraint-safe; billing variants nullable).
2. Data-migrate: split existing "First Last" values on the first space.
3. Remove the old combined-name fields.

The model-level clean() validation (blank=False for shipping names, required
when billing_same_as_shipping=False for billing names) is handled by Django at
save time, not at the DB level, so no NOT NULL constraint is added after the
data-migrate step.
"""

from django.db import migrations, models


def _split_name(full_name: str) -> tuple[str, str]:
    """Split 'First Last' → ('First', 'Last').  Handles blank input."""
    parts = (full_name or "").strip().split(" ", 1)
    if not parts or not parts[0]:
        return "", ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def forwards(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.all():
        first, last = _split_name(getattr(order, "shipping_name", "") or "")
        order.shipping_first_name = first
        order.shipping_last_name = last

        billing_name = getattr(order, "billing_name", None)
        if billing_name:
            b_first, b_last = _split_name(billing_name)
            order.billing_first_name = b_first
            order.billing_last_name = b_last

        order.save(update_fields=[
            "shipping_first_name", "shipping_last_name",
            "billing_first_name", "billing_last_name",
        ])


def backwards(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.all():
        first = order.shipping_first_name or ""
        last = order.shipping_last_name or ""
        order.shipping_name = f"{first} {last}".strip()

        b_first = order.billing_first_name or ""
        b_last = order.billing_last_name or ""
        order.billing_name = f"{b_first} {b_last}".strip() or None

        order.save(update_fields=["shipping_name", "billing_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_order_business_address_fields"),
    ]

    operations = [
        # 1. Add new fields
        migrations.AddField(
            model_name="order",
            name="shipping_first_name",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_last_name",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="billing_first_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="billing_last_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        # 2. Populate from old fields
        migrations.RunPython(forwards, reverse_code=backwards),
        # 3. Remove old fields
        migrations.RemoveField(model_name="order", name="shipping_name"),
        migrations.RemoveField(model_name="order", name="billing_name"),
    ]
