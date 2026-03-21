from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("carts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="claimed_offer_token",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Token of the most recently claimed CAMPAIGN_APPLY offer for this cart. "
                    "Mirrors the campaign_offer_token cookie and enables best-for-customer "
                    "comparison during guest\u2192authenticated cart merge."
                ),
                max_length=64,
                null=True,
            ),
        ),
    ]
