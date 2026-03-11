# Generated manually for Phase 3 — OrderItem pricing snapshot schema expansion.
# Adds nullable snapshot fields for the new pricing pipeline.
# All fields are nullable to allow safe migration of existing rows.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orderitems", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="unit_price_net_at_order_time",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Net unit price captured at order time (excl. tax).",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit_price_gross_at_order_time",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Gross unit price captured at order time (incl. tax, after promotion).",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="tax_amount_at_order_time",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Per-unit tax amount captured at order time.",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="tax_rate_at_order_time",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Effective tax rate percentage at order time (e.g. 23.0000 for 23 %).",
                max_digits=6,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="promotion_code_at_order_time",
            field=models.CharField(
                blank=True,
                help_text="Promotion code applied to this item at order time, if any.",
                max_length=100,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="promotion_type_at_order_time",
            field=models.CharField(
                blank=True,
                help_text="Type of promotion applied to this item at order time, if any.",
                max_length=32,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="promotion_discount_gross_at_order_time",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Gross discount amount from the applied promotion at order time.",
                max_digits=10,
                null=True,
            ),
        ),
    ]
