from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_address_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='company_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Business / trade registration number (optional).',
                max_length=64,
            ),
            preserve_default=False,
        ),
    ]
