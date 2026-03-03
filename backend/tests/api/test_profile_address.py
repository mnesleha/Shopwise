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