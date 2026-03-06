import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from accounts.models import CustomerProfile, Address


@pytest.mark.django_db
@pytest.mark.sqlite
def test_profile_is_auto_created_for_new_user_via_signal():
    """
    Contract:
    A CustomerProfile is automatically created when a User is created.
    """

    User = get_user_model()
    user = User.objects.create_user(email="p1@example.com", password="Passw0rd!123")

    profile = CustomerProfile.objects.get(user=user)
    assert profile.user_id == user.id


@pytest.mark.django_db
@pytest.mark.sqlite
def test_profile_is_one_to_one_with_user():
    """
    Contract:
    CustomerProfile is 1:1 with User (unique per user).
    """

    User = get_user_model()
    user = User.objects.create_user(email="p2@example.com", password="Passw0rd!123")

    # existing profile created by signal
    assert CustomerProfile.objects.filter(user=user).count() == 1

    # attempting to create another profile for the same user must fail
    with pytest.raises(IntegrityError):
        CustomerProfile.objects.create(user=user)


def _create_address(*, profile, **overrides):
    """
    Helper: create a valid Address with required fields.
    """

    data = {
        "profile": profile,
        "first_name": "John",
        "last_name": "Doe",
        "street_line_1": "Main Street 1",
        "street_line_2": "",
        "city": "Prague",
        "postal_code": "11000",
        "country": "CZ",
        "company": "",
        "vat_id": "",
    }
    data.update(overrides)
    return Address.objects.create(**data)


@pytest.mark.django_db
@pytest.mark.sqlite
def test_user_can_have_multiple_addresses():
    """
    Contract:
    User (via profile) can have multiple addresses (1:N).
    """

    User = get_user_model()
    user = User.objects.create_user(email="p3@example.com", password="Passw0rd!123")
    profile = CustomerProfile.objects.get(user=user)

    a1 = _create_address(profile=profile, street_line_1="A 1")
    a2 = _create_address(profile=profile, street_line_1="A 2")

    assert Address.objects.filter(profile=profile).count() == 2
    assert {a1.id, a2.id} == set(Address.objects.filter(profile=profile).values_list("id", flat=True))


@pytest.mark.django_db
@pytest.mark.sqlite
def test_profile_can_set_default_shipping_and_billing_addresses():
    """
    Contract:
    Profile supports default shipping and billing address selection.
    """

    User = get_user_model()
    user = User.objects.create_user(email="p4@example.com", password="Passw0rd!123")
    profile = CustomerProfile.objects.get(user=user)

    shipping = _create_address(profile=profile, street_line_1="Ship 1")
    billing = _create_address(profile=profile, street_line_1="Bill 1")

    profile.default_shipping_address = shipping
    profile.default_billing_address = billing
    profile.full_clean()
    profile.save()

    profile.refresh_from_db()
    assert profile.default_shipping_address_id == shipping.id
    assert profile.default_billing_address_id == billing.id


@pytest.mark.django_db
@pytest.mark.sqlite
def test_profile_rejects_default_address_that_belongs_to_another_user():
    """
    Contract:
    Default addresses must belong to the same profile/user.
    """

    User = get_user_model()
    u1 = User.objects.create_user(email="p5a@example.com", password="Passw0rd!123")
    u2 = User.objects.create_user(email="p5b@example.com", password="Passw0rd!123")
    p1 = CustomerProfile.objects.get(user=u1)
    p2 = CustomerProfile.objects.get(user=u2)

    foreign_address = _create_address(profile=p2, street_line_1="Foreign 1")

    p1.default_shipping_address = foreign_address

    with pytest.raises(ValidationError):
        p1.full_clean()


@pytest.mark.django_db
@pytest.mark.sqlite
def test_deleting_user_cascades_to_profile_and_addresses():
    """
    Contract:
    Deleting a User cascades to CustomerProfile and its Addresses.
    """

    User = get_user_model()
    user = User.objects.create_user(email="p6@example.com", password="Passw0rd!123")
    profile = CustomerProfile.objects.get(user=user)

    _create_address(profile=profile, street_line_1="Addr 1")
    _create_address(profile=profile, street_line_1="Addr 2")

    assert CustomerProfile.objects.filter(user=user).exists()
    assert Address.objects.filter(profile=profile).count() == 2

    user_id = user.id
    profile_id = profile.id
    user.delete()

    assert not CustomerProfile.objects.filter(id=profile_id).exists()
    assert Address.objects.filter(profile_id=profile_id).count() == 0

    # sanity check: user is gone
    assert not User.objects.filter(id=user_id).exists()


@pytest.mark.django_db
@pytest.mark.sqlite
def test_deleting_default_address_sets_default_to_null():
    """
    Contract:
    If a default address is deleted, the profile defaults are set to NULL.
    (Recommended minimal behavior via on_delete=SET_NULL.)
    """

    User = get_user_model()
    user = User.objects.create_user(email="p7@example.com", password="Passw0rd!123")
    profile = CustomerProfile.objects.get(user=user)

    addr = _create_address(profile=profile, street_line_1="Default 1")
    profile.default_shipping_address = addr
    profile.default_billing_address = addr
    profile.full_clean()
    profile.save()

    addr.delete()
    profile.refresh_from_db()

    assert profile.default_shipping_address is None
    assert profile.default_billing_address is None