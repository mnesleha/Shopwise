import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


@pytest.mark.django_db
@pytest.mark.sqlite
def test_address_has_first_and_last_name_fields():
    """
    Contract:
    Address stores recipient name split as first_name + last_name (not full_name).
    """
    from accounts.models import CustomerProfile, Address

    User = get_user_model()
    user = User.objects.create_user(email="addr_m_1@example.com", password="Passw0rd!123")
    profile = CustomerProfile.objects.get(user=user)

    addr = Address.objects.create(
        profile=profile,
        first_name="John",
        last_name="Doe",
        street_line_1="Main 1",
        street_line_2="",
        city="Prague",
        postal_code="11000",
        country="CZ",
        company="",
        vat_id="",
    )

    assert addr.first_name == "John"
    assert addr.last_name == "Doe"
    assert not hasattr(addr, "full_name")


@pytest.mark.django_db
@pytest.mark.sqlite
def test_profile_rejects_default_address_from_other_profile_even_after_name_split():
    """
    Contract:
    Default address must belong to the same profile.
    """
    from accounts.models import CustomerProfile, Address

    User = get_user_model()
    u1 = User.objects.create_user(email="addr_m_2a@example.com", password="Passw0rd!123")
    u2 = User.objects.create_user(email="addr_m_2b@example.com", password="Passw0rd!123")
    p1 = CustomerProfile.objects.get(user=u1)
    p2 = CustomerProfile.objects.get(user=u2)

    foreign = Address.objects.create(
        profile=p2,
        first_name="Jane",
        last_name="Foreign",
        street_line_1="Foreign 1",
        street_line_2="",
        city="Brno",
        postal_code="60200",
        country="CZ",
        company="",
        vat_id="",
    )

    p1.default_shipping_address = foreign
    with pytest.raises(ValidationError):
        p1.full_clean()