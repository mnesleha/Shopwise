# Generated migration — adds short_description and full_description to Product.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0002_product_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="short_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="full_description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
