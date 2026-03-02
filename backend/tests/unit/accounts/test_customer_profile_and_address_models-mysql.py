import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import CustomerProfile

@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_profile_signal_is_idempotent_get_or_create():
    """
    MySQL-only (recommended):
    Ensure the post_save(User) signal uses get_or_create and does not crash
    if the profile already exists.
    """

    User = get_user_model()
    user = User.objects.create_user(email="mx1@example.com", password="Passw0rd!123")

    # profile exists due to signal
    assert CustomerProfile.objects.filter(user=user).count() == 1

    # Manually trigger a "second creation attempt" pattern:
    # Re-saving the user should not attempt to create a second profile (if signal checks created),
    # but this test mainly guards implementation that uses get_or_create in any case.
    with transaction.atomic():
        user.first_name = "Changed"
        user.save()

    assert CustomerProfile.objects.filter(user=user).count() == 1