from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_order_order_discount_snapshot'),
    ]

    operations = [
        # Shipping business address snapshot fields
        migrations.AddField(
            model_name='order',
            name='shipping_company',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_company_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_vat_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        # Billing business address snapshot fields
        migrations.AddField(
            model_name='order',
            name='billing_company',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='billing_company_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='billing_vat_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
