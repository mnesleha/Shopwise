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
