import django_countries.fields
from django.db import migrations


class Migration(migrations.Migration):
    """
    Change Address.country from plain CharField(max_length=2) to
    django_countries.fields.CountryField.

    The underlying DB column stays VARCHAR(2) — this migration only updates
    Django's model state to use CountryField validation.
    """

    dependencies = [
        ("accounts", "0004_address_split_full_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="address",
            name="country",
            field=django_countries.fields.CountryField(max_length=2),
        ),
    ]
