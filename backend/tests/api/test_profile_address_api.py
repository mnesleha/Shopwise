import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@pytest.mark.sqlite
class TestProfileAndAddressAPI:
    PROFILE_URL = "/api/v1/profile/"
    ADDRESSES_URL = "/api/v1/addresses/"

    def _client(self) -> APIClient:
        return APIClient()

    def _create_user(self, email: str = "user@example.com", password: str = "Passw0rd!123"):
        User = get_user_model()
        return User.objects.create_user(email=email, password=password)

    def _auth_client(self, user):
        client = self._client()
        client.force_authenticate(user=user)
        return client

    def _create_address_payload(self, **overrides):
        data = {
            "full_name": "John Doe",
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

    def _create_address_for_user_via_api(self, client: APIClient, **overrides):
        payload = self._create_address_payload(**overrides)
        resp = client.post(self.ADDRESSES_URL, payload, format="json")
        assert resp.status_code == 201, resp.data
        return resp.data

    def test_anonymous_cannot_access_profile(self):
        client = self._client()
        resp = client.get(self.PROFILE_URL)
        assert resp.status_code == 401

    def test_authenticated_can_get_profile(self):
        user = self._create_user("p_api_1@example.com")
        client = self._auth_client(user)

        resp = client.get(self.PROFILE_URL)
        assert resp.status_code == 200, resp.data

        # Minimal contract: defaults exist and are nullable.
        assert "id" in resp.data
        assert resp.data["default_shipping_address"] is None
        assert resp.data["default_billing_address"] is None

    def test_anonymous_cannot_access_addresses(self):
        client = self._client()
        resp = client.get(self.ADDRESSES_URL)
        assert resp.status_code == 401

        resp = client.post(self.ADDRESSES_URL, self._create_address_payload(), format="json")
        assert resp.status_code == 401

    def test_authenticated_can_create_and_list_own_addresses(self):
        user = self._create_user("p_api_2@example.com")
        client = self._auth_client(user)

        a1 = self._create_address_for_user_via_api(client, street_line_1="Addr 1")
        a2 = self._create_address_for_user_via_api(client, street_line_1="Addr 2")

        resp = client.get(self.ADDRESSES_URL)
        assert resp.status_code == 200, resp.data

        ids = {item["id"] for item in resp.data}
        assert {a1["id"], a2["id"]}.issubset(ids)

        # Ensure server returns expected fields
        sample = resp.data[0]
        for field in [
            "id",
            "full_name",
            "street_line_1",
            "street_line_2",
            "city",
            "postal_code",
            "country",
            "company",
            "vat_id",
        ]:
            assert field in sample

    def test_addresses_list_is_scoped_to_authenticated_user(self):
        u1 = self._create_user("p_api_3a@example.com")
        u2 = self._create_user("p_api_3b@example.com")

        c1 = self._auth_client(u1)
        c2 = self._auth_client(u2)

        a1 = self._create_address_for_user_via_api(c1, street_line_1="U1 Only")
        _ = self._create_address_for_user_via_api(c2, street_line_1="U2 Only")

        resp = c1.get(self.ADDRESSES_URL)
        assert resp.status_code == 200, resp.data
        ids = {item["id"] for item in resp.data}

        assert a1["id"] in ids
        # must not include u2 address
        assert len(ids) == 1

    def test_user_cannot_retrieve_other_users_address_detail(self):
        u1 = self._create_user("p_api_4a@example.com")
        u2 = self._create_user("p_api_4b@example.com")

        c1 = self._auth_client(u1)
        c2 = self._auth_client(u2)

        foreign = self._create_address_for_user_via_api(c2, street_line_1="Foreign")

        # Expect 404 to avoid leaking existence (preferred)
        resp = c1.get(f"{self.ADDRESSES_URL}{foreign['id']}/")
        assert resp.status_code in (403, 404)
        assert resp.status_code == 404

    def test_user_cannot_update_other_users_address(self):
        u1 = self._create_user("p_api_5a@example.com")
        u2 = self._create_user("p_api_5b@example.com")

        c1 = self._auth_client(u1)
        c2 = self._auth_client(u2)

        foreign = self._create_address_for_user_via_api(c2, street_line_1="Foreign")

        resp = c1.patch(
            f"{self.ADDRESSES_URL}{foreign['id']}/",
            {"city": "Hacked"},
            format="json",
        )
        assert resp.status_code == 404

    def test_user_can_update_own_address(self):
        user = self._create_user("p_api_6@example.com")
        client = self._auth_client(user)

        addr = self._create_address_for_user_via_api(client, city="Prague")

        resp = client.patch(
            f"{self.ADDRESSES_URL}{addr['id']}/",
            {"city": "Brno", "company": "ACME"},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["city"] == "Brno"
        assert resp.data["company"] == "ACME"

    def test_profile_can_set_default_addresses_to_own_addresses(self):
        user = self._create_user("p_api_7@example.com")
        client = self._auth_client(user)

        ship = self._create_address_for_user_via_api(client, street_line_1="Ship")
        bill = self._create_address_for_user_via_api(client, street_line_1="Bill")

        resp = client.patch(
            self.PROFILE_URL,
            {
                "default_shipping_address": ship["id"],
                "default_billing_address": bill["id"],
            },
            format="json",
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["default_shipping_address"] == ship["id"]
        assert resp.data["default_billing_address"] == bill["id"]

    def test_profile_rejects_setting_default_address_to_foreign_address(self):
        u1 = self._create_user("p_api_8a@example.com")
        u2 = self._create_user("p_api_8b@example.com")

        c1 = self._auth_client(u1)
        c2 = self._auth_client(u2)

        foreign = self._create_address_for_user_via_api(c2, street_line_1="Foreign")

        resp = c1.patch(
            self.PROFILE_URL,
            {"default_shipping_address": foreign["id"]},
            format="json",
        )
        assert resp.status_code == 400, resp.data

    def test_deleting_default_address_nulls_profile_defaults_via_api(self):
        user = self._create_user("p_api_9@example.com")
        client = self._auth_client(user)

        addr = self._create_address_for_user_via_api(client, street_line_1="Default")

        # Set as default shipping & billing
        resp = client.patch(
            self.PROFILE_URL,
            {"default_shipping_address": addr["id"], "default_billing_address": addr["id"]},
            format="json",
        )
        assert resp.status_code == 200, resp.data

        # Delete address
        resp = client.delete(f"{self.ADDRESSES_URL}{addr['id']}/")
        assert resp.status_code in (204, 200)

        # Verify profile defaults are null
        resp = client.get(self.PROFILE_URL)
        assert resp.status_code == 200, resp.data
        assert resp.data["default_shipping_address"] is None
        assert resp.data["default_billing_address"] is None

    def test_address_create_does_not_allow_overriding_profile_in_payload(self):
        """
        Contract:
        Address must belong to exactly one authenticated user.
        Client must not be able to create address for another user by sending profile/user fields.
        """
        u1 = self._create_user("p_api_10a@example.com")
        u2 = self._create_user("p_api_10b@example.com")

        c1 = self._auth_client(u1)

        # Attempt to sneak in profile/user ownership via payload
        payload = self._create_address_payload(street_line_1="Sneaky")
        payload["profile"] = 999999
        payload["user"] = 999999

        resp = c1.post(self.ADDRESSES_URL, payload, format="json")
        assert resp.status_code == 201, resp.data

        # Ensure it is still owned by u1 (by listing u1 addresses; should contain exactly 1)
        resp = c1.get(self.ADDRESSES_URL)
        assert resp.status_code == 200, resp.data
        assert len(resp.data) == 1
        assert resp.data[0]["street_line_1"] == "Sneaky"