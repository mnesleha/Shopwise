"""Phase 3 Slice 5 — product name snapshot + line total net/gross snapshot.

Adds three nullable fields to OrderItem:
  - product_name_at_order_time: captured product name for stable order history
  - line_total_net_at_order_time:  net  line total (unit_net × qty)
  - line_total_gross_at_order_time: gross line total (unit_gross × qty)
All nullable for safe migration of existing records.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orderitems", "0002_orderitem_pricing_snapshot_phase3"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="product_name_at_order_time",
            field=models.CharField(
                blank=True,
                help_text="Product name captured at order time. Use this for order history instead of the live product name.",
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="line_total_net_at_order_time",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Net line total (unit net price × quantity) captured at order time.",
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="line_total_gross_at_order_time",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Gross line total (unit gross price × quantity) captured at order time.",
                max_digits=12,
                null=True,
            ),
        ),
    ]
