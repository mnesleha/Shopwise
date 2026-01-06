import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError


@pytest.mark.django_db
def test_custom_user_model_has_email_as_username_field():
    User = get_user_model()
    assert getattr(User, "USERNAME_FIELD", None) == "email"


@pytest.mark.django_db
def test_create_user_requires_email():
    User = get_user_model()

    with pytest.raises((TypeError, ValueError)):
        User.objects.create_user(email=None, password="Passw0rd!123")


@pytest.mark.django_db
def test_email_is_unique_at_db_level():
    User = get_user_model()

    User.objects.create_user(
        email="unique@example.com",
        password="Passw0rd!123",
        first_name="A",
        last_name="B",
    )

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="unique@example.com",
            password="Passw0rd!123",
            first_name="C",
            last_name="D",
        )


@pytest.mark.django_db
def test_email_is_normalized_to_lowercase():
    """
    Business contract:
    Email identity is case-insensitive; stored form is normalized.
    """
    User = get_user_model()

    u = User.objects.create_user(
        email="MiXeD@Example.COM",
        password="Passw0rd!123",
        first_name="A",
        last_name="B",
    )
    assert u.email == "mixed@example.com"


@pytest.mark.django_db
def test_display_name_falls_back_to_email_when_first_last_missing():
    """
    Model-level expectation for UI display:
    - prefer first_name + last_name
    - else fallback to email
    """
    User = get_user_model()

    u = User.objects.create_user(
        email="display@example.com",
        password="Passw0rd!123",
        first_name="",
        last_name="",
    )

    # This assumes you implement a convenience property like `display_name`
    # If you don't want such a property on the model, delete this test.
    assert hasattr(u, "display_name")
    assert u.display_name == "display@example.com"


@pytest.mark.django_db
def test_display_name_uses_first_and_last_name_when_present():
    User = get_user_model()

    u = User.objects.create_user(
        email="named@example.com",
        password="Passw0rd!123",
        first_name="John",
        last_name="Doe",
    )
    assert hasattr(u, "display_name")
    assert u.display_name == "John Doe"
