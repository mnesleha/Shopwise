"""
Tests for /api/v1/profile/ with legacy users (no CustomerProfile in DB).

Covers:
 - GET must not 500 when no CustomerProfile exists (auto-creates it).
 - PATCH with a foreign address must return 400.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import Address, CustomerProfile

User = get_user_model()

PROFILE_URL = "/api/v1/profile/"

# Minimal valid address payload for helper factories.
_ADDRESS_PAYLOAD = {
    "first_name": "Test",
    "last_name": "User",
    "street_line_1": "123 Main St",
    "street_line_2": "",
    "city": "Springfield",
    "postal_code": "12345",
    "country": "US",
    "company": "",
    "vat_id": "",
}


def _create_user(email: str, password: str = "Passw0rd!123"):
    return User.objects.create_user(email=email, password=password)


def _auth_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _create_address_for_user(user) -> Address:
    """Create a CustomerProfile (if needed) and an Address for *user*."""
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    return Address.objects.create(profile=profile, **_ADDRESS_PAYLOAD)


@pytest.mark.django_db
@pytest.mark.sqlite
class TestProfileLegacyUserNoProfile:
    def test_get_profile_legacy_user_without_profile_returns_200(self):
        """
        A legacy user whose CustomerProfile was never created must not cause
        a 500 on GET /api/v1/profile/.

        Expected behaviour:
         - HTTP 200
         - A new CustomerProfile row is inserted into DB automatically.
        """
        user = _create_user("legacy@example.com")

        # Simulate legacy state: delete the profile that the post_save signal
        # created when the user was saved.
        CustomerProfile.objects.filter(user=user).delete()
        assert not CustomerProfile.objects.filter(user=user).exists()

        client = _auth_client(user)
        response = client.get(PROFILE_URL)

        assert response.status_code == 200, response.data

        # Profile must have been auto-created by the view.
        assert CustomerProfile.objects.filter(user=user).exists()

    def test_patch_default_shipping_with_foreign_address_returns_400(self):
        """
        Supplying a default_shipping_address that belongs to a different user
        must return HTTP 400 (not silently accept it).
        """
        u1 = _create_user("u1@example.com")
        u2 = _create_user("u2@example.com")

        # Create an address that belongs to u2, not u1.
        foreign_address = _create_address_for_user(u2)

        client = _auth_client(u1)
        response = client.patch(
            PROFILE_URL,
            {"default_shipping_address": foreign_address.id},
            format="json",
        )

        assert response.status_code == 400, response.data
