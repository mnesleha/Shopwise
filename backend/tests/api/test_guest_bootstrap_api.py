"""
Tests for POST /api/v1/guest/orders/{id}/bootstrap/ and the
email_account_exists field added to GET /api/v1/guest/orders/{id}/.

Coverage:
1. Verified guest order + new email → account created, profile exists,
   addresses seeded, user is logged in, current order claimed.
2. Verified guest order + existing registered email → 409, no duplicate account.
3. Address seeding is best-effort: account creation succeeds even when
   snapshot data is missing/unavailable.
4. Unverified/non-eligible access (bad token, no token) → 404, no account.
5. GET response includes email_account_exists flag.
6. Bootstrap with mismatched passwords → 400.
7. After bootstrap, additional guest orders with the same email are claimed.
"""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

from accounts.models import Address, CustomerProfile
from orders.models import Order
from orders.services.guest_order_access_service import GuestOrderAccessService
from tests.conftest import create_valid_order

pytestmark = pytest.mark.django_db

User = get_user_model()

_GUEST_DETAIL_URL = "/api/v1/guest/orders/{order_id}/"

_BOOTSTRAP_PAYLOAD = {
    "password": "Str0ngP@ss!",
    "password_confirm": "Str0ngP@ss!",
}


def _make_guest_order(email="guest@example.com", **overrides):
    """Create a guest order and issue a capability token; return (order, token)."""
    order = create_valid_order(
        user=None,
        status=Order.Status.CREATED,
        customer_email=email,
        **overrides,
    )
    token = GuestOrderAccessService.issue_token(order=order)
    return order, token


def _bootstrap_url(order_id, token):
    """Return the full bootstrap URL with the token as a query parameter."""
    return f"/api/v1/guest/orders/{order_id}/bootstrap/?token={token}"


# ---------------------------------------------------------------------------
# GET: email_account_exists field
# ---------------------------------------------------------------------------


def test_guest_order_retrieve_email_account_exists_false(client):
    order, token = _make_guest_order(email="newguest@example.com")
    resp = client.get(_GUEST_DETAIL_URL.format(order_id=order.id), {"token": token})
    assert resp.status_code == 200
    assert resp.json()["email_account_exists"] is False


def test_guest_order_retrieve_email_account_exists_true(client):
    email = "existing@example.com"
    User.objects.create_user(email=email, password="Password!1")
    order, token = _make_guest_order(email=email)
    resp = client.get(_GUEST_DETAIL_URL.format(order_id=order.id), {"token": token})
    assert resp.status_code == 200
    assert resp.json()["email_account_exists"] is True


# ---------------------------------------------------------------------------
# 1. Success path: new email → account created, profile, addresses, logged in,
#    current order claimed
# ---------------------------------------------------------------------------


def test_bootstrap_creates_account_for_new_email(client):
    order, token = _make_guest_order(email="brand@new.com")

    resp = client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )

    assert resp.status_code == 201, resp.content
    data = resp.json()
    assert data["is_authenticated"] is True
    assert data["email"] == "brand@new.com"
    assert data["email_verified"] is True


def test_bootstrap_profile_created(client):
    order, token = _make_guest_order(email="profile@new.com")
    client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    user = User.objects.get(email="profile@new.com")
    assert CustomerProfile.objects.filter(user=user).exists()


def test_bootstrap_addresses_seeded_from_order(client):
    """Default shipping and billing addresses are seeded from the order snapshot."""
    order, token = _make_guest_order(
        email="addr@seed.com",
        shipping_first_name="Alice",
        shipping_last_name="Smith",
    )
    client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    user = User.objects.get(email="addr@seed.com")
    profile = CustomerProfile.objects.get(user=user)
    assert profile.default_shipping_address is not None
    assert profile.default_billing_address is not None
    assert Address.objects.filter(profile=profile).count() >= 2

    shipping = profile.default_shipping_address
    assert shipping.street_line_1 == order.shipping_address_line1
    assert shipping.city == order.shipping_city


# ---------------------------------------------------------------------------
# 1b. Country normalisation during address seeding
# ---------------------------------------------------------------------------


def test_bootstrap_address_country_from_full_name(client):
    """
    Full country name in the order snapshot (e.g. 'Czech Republic') is
    resolved to a 2-char ISO code before being stored in Address.country.
    This prevents DataError on DB columns with max_length=2.
    """
    order, token = _make_guest_order(
        email="country_name@seed.com",
        shipping_country="Czech Republic",
    )
    client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    user = User.objects.get(email="country_name@seed.com")
    profile = CustomerProfile.objects.get(user=user)
    shipping = profile.default_shipping_address
    assert shipping is not None
    assert str(shipping.country) == "CZ"


def test_bootstrap_address_country_iso_code_unchanged(client):
    """
    A correctly formatted 2-char ISO code passes through unmodified.
    """
    order, token = _make_guest_order(
        email="country_code@seed.com",
        shipping_country="DE",
    )
    client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    user = User.objects.get(email="country_code@seed.com")
    profile = CustomerProfile.objects.get(user=user)
    shipping = profile.default_shipping_address
    assert shipping is not None
    assert str(shipping.country) == "DE"


def test_bootstrap_address_unrecognised_country_stored_blank(client):
    """
    An unrecognisable country string is stored as '' (blank) — the account
    is still created successfully without a DataError.
    """
    order, token = _make_guest_order(
        email="country_unknown@seed.com",
        shipping_country="NotACountry",
    )
    resp = client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.content
    user = User.objects.get(email="country_unknown@seed.com")
    profile = CustomerProfile.objects.get(user=user)
    shipping = profile.default_shipping_address
    assert shipping is not None
    assert str(shipping.country) == ""


def test_bootstrap_current_order_becomes_claimed(client):
    """After bootstrap the triggering order is assigned to the new user."""
    order, token = _make_guest_order(email="claim@test.com")

    client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )

    user = User.objects.get(email="claim@test.com")
    order.refresh_from_db()
    assert order.user_id == user.pk
    assert order.is_claimed is True


def test_bootstrap_auth_cookies_set(client):
    from django.conf import settings as django_settings

    order, token = _make_guest_order(email="cookie@test.com")
    resp = client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    assert django_settings.AUTH_COOKIE_ACCESS in resp.cookies
    assert django_settings.AUTH_COOKIE_REFRESH in resp.cookies


def test_bootstrap_first_last_name_from_shipping_fields(client):
    """First/last name on the new account is taken directly from the order shipping name fields."""
    order, token = _make_guest_order(
        email="name@test.com",
        shipping_first_name="John",
        shipping_last_name="Doe",
    )
    client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    user = User.objects.get(email="name@test.com")
    assert user.first_name == "John"
    assert user.last_name == "Doe"


# ---------------------------------------------------------------------------
# 7. Additional guest orders with the same email are claimed
# ---------------------------------------------------------------------------


def test_bootstrap_claims_all_guest_orders_with_same_email(client):
    """
    If the same email has multiple unclaimed guest orders, the bootstrap
    endpoint claims them all via the existing claim_guest_orders_for_user
    infrastructure.
    """
    email = "multi@orders.com"
    order1, token = _make_guest_order(email=email)
    order2 = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email=email
    )

    client.post(
        _bootstrap_url(order1.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )

    user = User.objects.get(email=email)
    order1.refresh_from_db()
    order2.refresh_from_db()
    assert order1.user_id == user.pk
    assert order2.user_id == user.pk
    assert order2.is_claimed is True


# ---------------------------------------------------------------------------
# 2. Existing-account path → 409, no duplicate account
# ---------------------------------------------------------------------------


def test_bootstrap_existing_email_returns_409(client):
    email = "existing@account.com"
    User.objects.create_user(email=email, password="Original!1")

    order, token = _make_guest_order(email=email)
    resp = client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "EMAIL_ALREADY_REGISTERED"


def test_bootstrap_existing_email_does_not_create_duplicate(client):
    email = "existing2@account.com"
    User.objects.create_user(email=email, password="Original!1")

    order, token = _make_guest_order(email=email)
    client.post(
        _bootstrap_url(order.id, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )

    assert User.objects.filter(email=email).count() == 1


# ---------------------------------------------------------------------------
# 3. Address seeding best-effort: account creation succeeds even on failure
# ---------------------------------------------------------------------------


def test_bootstrap_succeeds_even_if_address_seeding_fails(client):
    """Account creation must not be rolled back if address seeding raises."""
    order, token = _make_guest_order(email="noaddr@test.com")

    with patch(
        "api.views.guest_orders.seed_addresses_from_order",
        side_effect=Exception("simulated address seeding failure"),
    ):
        resp = client.post(
            _bootstrap_url(order.id, token),
            data=_BOOTSTRAP_PAYLOAD,
            content_type="application/json",
        )

    assert resp.status_code == 201, resp.content
    assert User.objects.filter(email="noaddr@test.com").exists()


def test_bootstrap_succeeds_with_no_addresses_when_seeding_fails(client):
    """When seeding fails, profile addresses stay empty but signup completes."""
    order, token = _make_guest_order(email="noaddr2@test.com")

    with patch(
        "api.views.guest_orders.seed_addresses_from_order",
        side_effect=Exception("simulated"),
    ):
        resp = client.post(
            _bootstrap_url(order.id, token),
            data=_BOOTSTRAP_PAYLOAD,
            content_type="application/json",
        )

    assert resp.status_code == 201
    user = User.objects.get(email="noaddr2@test.com")
    profile = CustomerProfile.objects.filter(user=user).first()
    if profile:
        assert profile.default_shipping_address is None
        assert profile.default_billing_address is None


# ---------------------------------------------------------------------------
# 4. Unverified/non-eligible access
# ---------------------------------------------------------------------------


def test_bootstrap_missing_token_returns_404(client):
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="notoken@test.com"
    )
    resp = client.post(
        f"/api/v1/guest/orders/{order.id}/bootstrap/",
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_bootstrap_invalid_token_returns_404(client):
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="badtoken@test.com"
    )
    resp = client.post(
        f"/api/v1/guest/orders/{order.id}/bootstrap/?token=invalid",
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_bootstrap_wrong_order_id_returns_404(client):
    order, token = _make_guest_order(email="wrongid@test.com")
    resp = client.post(
        _bootstrap_url(order.id + 99999, token),
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_bootstrap_non_guest_order_returns_404(client, user):
    """Bootstrap must not work on orders that already have a user."""
    order = create_valid_order(
        user=user, status=Order.Status.CREATED, customer_email=user.email
    )
    resp = client.post(
        f"/api/v1/guest/orders/{order.id}/bootstrap/?token=anything",
        data=_BOOTSTRAP_PAYLOAD,
        content_type="application/json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Password validation
# ---------------------------------------------------------------------------


def test_bootstrap_mismatched_passwords_returns_400(client):
    order, token = _make_guest_order(email="pwmismatch@test.com")
    resp = client.post(
        _bootstrap_url(order.id, token),
        data={"password": "abc123", "password_confirm": "different"},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_bootstrap_missing_password_returns_400(client):
    order, token = _make_guest_order(email="nopw@test.com")
    resp = client.post(
        _bootstrap_url(order.id, token),
        data={"password_confirm": "abc123"},
        content_type="application/json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 7. Rate limiting
# ---------------------------------------------------------------------------


def test_bootstrap_protected_by_ip_rate_limit(client, settings):
    """Repeated bootstrap attempts from the same IP are throttled with 429."""
    settings.DISABLE_RATE_LIMITING_FOR_TESTS = False
    settings.BOOTSTRAP_RL_PER_IP = 1
    settings.BOOTSTRAP_RL_WINDOW_S = 60

    order, token = _make_guest_order(email="rl_ip@test.com")
    invalid_payload = {"password": "abc", "password_confirm": "xyz"}  # mismatch → 400, order not claimed

    # First request: counter = 1 ≤ limit (1) → not yet throttled, fails at serializer
    client.post(_bootstrap_url(order.id, token), data=invalid_payload, content_type="application/json")

    # Second request: counter = 2 > limit (1) → 429
    resp = client.post(_bootstrap_url(order.id, token), data=invalid_payload, content_type="application/json")
    assert resp.status_code == 429
    assert "Too many requests" in resp.json()["detail"]


def test_bootstrap_protected_by_token_rate_limit(client, settings):
    """Repeated bootstrap attempts with the same token are throttled with 429."""
    settings.DISABLE_RATE_LIMITING_FOR_TESTS = False
    settings.BOOTSTRAP_RL_PER_IP = 10000  # disable IP limit for this test
    settings.BOOTSTRAP_RL_WINDOW_S = 60
    settings.BOOTSTRAP_RL_PER_TOKEN = 1
    settings.BOOTSTRAP_RL_TOKEN_WINDOW_S = 60

    order, token = _make_guest_order(email="rl_tok@test.com")
    invalid_payload = {"password": "abc", "password_confirm": "xyz"}  # mismatch → 400, order not claimed

    # First request: token counter = 1 ≤ limit (1) → not yet throttled, fails at serializer
    client.post(_bootstrap_url(order.id, token), data=invalid_payload, content_type="application/json")

    # Second request: token counter = 2 > limit (1) → 429
    resp = client.post(_bootstrap_url(order.id, token), data=invalid_payload, content_type="application/json")
    assert resp.status_code == 429
    assert "Too many requests" in resp.json()["detail"]


def test_bootstrap_rate_limit_does_not_block_normal_request(client):
    """A single valid bootstrap request is still 201 (rate limiting does not block normal use)."""
    order, token = _make_guest_order(email="rl_ok@test.com")
    resp = client.post(_bootstrap_url(order.id, token), data=_BOOTSTRAP_PAYLOAD, content_type="application/json")
    assert resp.status_code == 201


def test_guest_order_retrieve_not_affected_by_bootstrap_rate_limit(client, settings):
    """Rate limiting on bootstrap does not affect the read-only guest order GET view."""
    settings.DISABLE_RATE_LIMITING_FOR_TESTS = False
    settings.BOOTSTRAP_RL_PER_IP = 1
    settings.BOOTSTRAP_RL_WINDOW_S = 60

    order, token = _make_guest_order(email="rl_get@test.com")
    invalid_payload = {"password": "abc", "password_confirm": "xyz"}  # mismatch; order remains unclaimed

    # Saturate the bootstrap IP limit (invalid payload so the order is never claimed)
    client.post(_bootstrap_url(order.id, token), data=invalid_payload, content_type="application/json")
    throttled = client.post(_bootstrap_url(order.id, token), data=invalid_payload, content_type="application/json")
    assert throttled.status_code == 429

    # GET (retrieve) should be completely unaffected — no rate limit on that view
    resp = client.get(_GUEST_DETAIL_URL.format(order_id=order.id), {"token": token})
    assert resp.status_code == 200
