import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.sqlite
class TestProfileAndAddressAPIV1:
    PROFILE_URL = "/api/v1/profile/"
    ADDRESSES_URL = "/api/v1/addresses/"

    def _client(self) -> APIClient:
        return APIClient()

    def _create_user(self, email: str, password: str = "Passw0rd!123"):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password)

    def _auth_client(self, user):
        c = self._client()
        c.force_authenticate(user=user)
        return c

    def _address_payload(self, **overrides):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "street_line_1": "Main Street 1",
            "street_line_2": "",
            "city": "Prague",
            "postal_code": "11000",
            "country": "CZ",
            "company": "",
            "vat_id": "",
            "phone": "+420123456789",
        }
        data.update(overrides)
        return data

    def test_authenticated_can_create_and_list_own_addresses(self):
        user = self._create_user("addr_api_1@example.com")
        c = self._auth_client(user)

        r1 = c.post(self.ADDRESSES_URL, self._address_payload(street_line_1="Addr 1"), format="json")
        assert r1.status_code == 201, r1.data
        assert "id" in r1.data
        assert r1.data["first_name"] == "John"
        assert r1.data["last_name"] == "Doe"

        r2 = c.get(self.ADDRESSES_URL)
        assert r2.status_code == 200, r2.data
        assert isinstance(r2.data, list)
        assert any(x["id"] == r1.data["id"] for x in r2.data)

        sample = r2.data[0]
        for field in [
            "id",
            "first_name",
            "last_name",
            "street_line_1",
            "street_line_2",
            "city",
            "postal_code",
            "country",
            "company",
            "vat_id",
            "phone",
        ]:
            assert field in sample

    def test_profile_patch_sets_default_addresses_by_id(self):
        user = self._create_user("addr_api_2@example.com")
        c = self._auth_client(user)

        a = c.post(self.ADDRESSES_URL, self._address_payload(), format="json")
        assert a.status_code == 201, a.data
        addr_id = a.data["id"]

        p = c.patch(self.PROFILE_URL, {"default_shipping_address": addr_id}, format="json")
        assert p.status_code == 200, p.data
        assert p.data["default_shipping_address"] == addr_id

    def test_profile_rejects_foreign_default_address(self):
        u1 = self._create_user("addr_api_3a@example.com")
        u2 = self._create_user("addr_api_3b@example.com")
        c1 = self._auth_client(u1)
        c2 = self._auth_client(u2)

        foreign = c2.post(self.ADDRESSES_URL, self._address_payload(first_name="Jane"), format="json")
        assert foreign.status_code == 201, foreign.data

        resp = c1.patch(self.PROFILE_URL, {"default_shipping_address": foreign.data["id"]}, format="json")
        assert resp.status_code == 400, resp.data

    # ------------------------------------------------------------------
    # Phone field tests
    # ------------------------------------------------------------------

    def test_create_address_with_phone_succeeds(self):
        user = self._create_user("addr_phone_1@example.com")
        c = self._auth_client(user)

        resp = c.post(self.ADDRESSES_URL, self._address_payload(phone="+420777111222"), format="json")
        assert resp.status_code == 201, resp.data
        assert resp.data["phone"] == "+420777111222"

    def test_create_address_without_phone_fails(self):
        user = self._create_user("addr_phone_2@example.com")
        c = self._auth_client(user)

        payload = self._address_payload()
        del payload["phone"]
        resp = c.post(self.ADDRESSES_URL, payload, format="json")
        assert resp.status_code == 400, resp.data
        assert "phone" in resp.data.get("errors", resp.data)

    def test_create_address_with_blank_phone_fails(self):
        user = self._create_user("addr_phone_3@example.com")
        c = self._auth_client(user)

        resp = c.post(self.ADDRESSES_URL, self._address_payload(phone=""), format="json")
        assert resp.status_code == 400, resp.data
        assert "phone" in resp.data.get("errors", resp.data)

    def test_patch_address_with_phone_succeeds(self):
        user = self._create_user("addr_phone_4@example.com")
        c = self._auth_client(user)

        create = c.post(self.ADDRESSES_URL, self._address_payload(), format="json")
        assert create.status_code == 201, create.data
        addr_id = create.data["id"]

        resp = c.patch(f"{self.ADDRESSES_URL}{addr_id}/", {"phone": "+420999888777"}, format="json")
        assert resp.status_code == 200, resp.data
        assert resp.data["phone"] == "+420999888777"

    def test_patch_address_with_blank_phone_fails(self):
        user = self._create_user("addr_phone_5@example.com")
        c = self._auth_client(user)

        create = c.post(self.ADDRESSES_URL, self._address_payload(), format="json")
        assert create.status_code == 201, create.data
        addr_id = create.data["id"]

        resp = c.patch(f"{self.ADDRESSES_URL}{addr_id}/", {"phone": ""}, format="json")
        assert resp.status_code == 400, resp.data
        assert "phone" in resp.data.get("errors", resp.data)

    def test_patch_address_without_phone_preserves_existing_phone(self):
        """PATCH without phone in payload must not clear the existing value."""
        user = self._create_user("addr_phone_6@example.com")
        c = self._auth_client(user)

        create = c.post(self.ADDRESSES_URL, self._address_payload(phone="+420123000000"), format="json")
        assert create.status_code == 201, create.data
        addr_id = create.data["id"]

        resp = c.patch(f"{self.ADDRESSES_URL}{addr_id}/", {"city": "Brno"}, format="json")
        assert resp.status_code == 200, resp.data
        assert resp.data["phone"] == "+420123000000"

    def test_legacy_address_without_phone_is_readable(self):
        """
        An address row created directly (bypassing the serializer) with no
        phone should still be readable via the API without errors.
        This simulates legacy data that existed before the phone field.
        """
        from accounts.models import Address, CustomerProfile

        user = self._create_user("addr_legacy_1@example.com")
        c = self._auth_client(user)
        profile, _ = CustomerProfile.objects.get_or_create(user=user)

        # Insert a legacy row with no phone (blank) directly, bypassing the
        # serializer layer.
        legacy = Address.objects.create(
            profile=profile,
            first_name="Legacy",
            last_name="User",
            street_line_1="Old Road 1",
            street_line_2="",
            city="Prague",
            postal_code="11000",
            country="CZ",
            company="",
            vat_id="",
            phone="",
        )

        resp = c.get(self.ADDRESSES_URL)
        assert resp.status_code == 200, resp.data
        found = next((a for a in resp.data if a["id"] == legacy.id), None)
        assert found is not None
        assert found["phone"] == ""