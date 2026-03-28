from django.db import migrations, models

import shipping.models


class Migration(migrations.Migration):

    dependencies = [
        ("shipping", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="shipment",
            name="label_file",
            field=models.FileField(blank=True, null=True, upload_to=shipping.models.shipment_label_upload_to),
        ),
    ]