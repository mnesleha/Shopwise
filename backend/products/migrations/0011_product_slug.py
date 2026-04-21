from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0010_django_prices_gross_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="Stable product identifier for seed data, tests, and storefront URLs.",
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
    ]