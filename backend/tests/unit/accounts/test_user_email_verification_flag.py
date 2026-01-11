import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_user_email_verified_defaults_to_false():
    User = get_user_model()

    user = User.objects.create_user(
        email="verify@example.com",
        password="Passw0rd!123",
    )

    assert user.email_verified is False


@pytest.mark.django_db
def test_superuser_email_verified_defaults_to_false(db):
    User = get_user_model()
    su = User.objects.create_superuser(
        email="admin@example.com", password="Passw0rd!123")
    assert su.email_verified is False
