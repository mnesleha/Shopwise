import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add EmailChangeRequest model for the secure email-change flow (ADR-035)."""

    dependencies = [
        ("accounts", "0005_address_country_field"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailChangeRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_change_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("old_email_snapshot", models.EmailField()),
                ("new_email", models.EmailField()),
                (
                    "confirm_token_hash",
                    models.CharField(db_index=True, max_length=64),
                ),
                (
                    "cancel_token_hash",
                    models.CharField(db_index=True, max_length=64),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "request_ip",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                ("user_agent", models.TextField(blank=True, null=True)),
                (
                    "_confirm_token_debug",
                    models.CharField(
                        blank=True,
                        db_column="confirm_token_debug",
                        max_length=128,
                        null=True,
                    ),
                ),
                (
                    "_cancel_token_debug",
                    models.CharField(
                        blank=True,
                        db_column="cancel_token_debug",
                        max_length=128,
                        null=True,
                    ),
                ),
            ],
        ),
    ]
