# Generated manually for Phase 3 — Order totals snapshot schema expansion.
# Adds nullable snapshot fields for the new pricing pipeline.
# All fields are nullable to allow safe migration of existing rows.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_order_guest_access_tokens"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="subtotal_net",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Sum of all item net prices at order time.",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="subtotal_gross",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Sum of all item gross prices at order time (incl. tax, after promotions).",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="total_tax",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total tax amount across all items at order time.",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="total_discount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total discount amount across all items at order time.",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="currency",
            field=models.CharField(
                blank=True,
                choices=[
                    ("EUR", "Euro"),
                    ("USD", "US Dollar"),
                    ("GBP", "British Pound"),
                    ("PLN", "Polish Zloty"),
                ],
                help_text="ISO 4217 currency code for all monetary snapshot fields on this order.",
                max_length=3,
                null=True,
            ),
        ),
    ]
