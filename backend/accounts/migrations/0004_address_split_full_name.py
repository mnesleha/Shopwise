from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Hard-break schema change: replace Address.full_name with
    Address.first_name + Address.last_name.

    No data migration is performed — development data is expected to be
    dropped and reseeded.  A temporary empty-string default is used only
    to satisfy the NOT NULL constraint when running against a non-empty
    table (e.g. MySQL); preserve_default=False removes it from the
    model state after the migration is applied.
    """

    dependencies = [
        ("accounts", "0003_fix_profile_default_address_fk_setnull"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="address",
            name="full_name",
        ),
        migrations.AddField(
            model_name="address",
            name="first_name",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="address",
            name="last_name",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
    ]
