"""Add order_discount_gross and order_promotion_code to Order.

Phase 4 / Slice 3: snapshot fields for the order-level AUTO_APPLY
promotion applied at checkout.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_order_totals_snapshot_phase3"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_discount_gross",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Phase 4: gross reduction from the order-level promotion applied at checkout. "
                    "Null when no order-level discount was applied."
                ),
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="order_promotion_code",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Phase 4: code of the OrderPromotion applied at checkout. "
                    "Null when no order-level discount was applied."
                ),
                max_length=50,
                null=True,
            ),
        ),
    ]
