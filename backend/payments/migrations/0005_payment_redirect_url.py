"""Add redirect_url field to Payment model.

This field stores the hosted-gateway redirect URL returned by providers such
as AcquireMock when a payment session is created.  Null for direct providers
(e.g. DEV_FAKE/COD) that do not use a hosted redirect flow.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0004_add_acquiremock_provider_choice"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="redirect_url",
            field=models.CharField(
                max_length=2048,
                null=True,
                blank=True,
            ),
        ),
    ]
