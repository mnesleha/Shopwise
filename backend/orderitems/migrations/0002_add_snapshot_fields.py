from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orderitems", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="applied_discount_type_at_order_time",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="applied_discount_value_at_order_time",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="line_total_at_order_time",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit_price_at_order_time",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
