from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_order_shipping_method_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("CREATED", "Created"),
                    ("PAID", "Paid"),
                    ("PAYMENT_FAILED", "Payment Failed"),
                    ("DELIVERY_FAILED", "Delivery failed"),
                    ("SHIPPED", "Shipped"),
                    ("DELIVERED", "Delivered"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="CREATED",
                max_length=20,
            ),
        ),
    ]