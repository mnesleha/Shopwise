from django.db import migrations, models


class Migration(migrations.Migration):
    """Add token_version to User for global session revocation (logout-all)."""

    dependencies = [
        ("accounts", "0006_emailchangerequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="token_version",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
