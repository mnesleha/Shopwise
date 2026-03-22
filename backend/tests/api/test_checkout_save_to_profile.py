"""
Tests for the save_to_profile feature in POST /api/v1/cart/checkout/.

When an authenticated user submits checkout with save_to_profile=True:
  - New Address records are created only when the effective checkout address
    differs from the current profile default (no-op protection).
  - CustomerProfile.default_shipping_address and default_billing_address are
    updated only for the sides that actually changed.

Guest users and save_to_profile=False are unaffected.
"""

import pytest
from products.models import Product
from accounts.models import Address, CustomerProfile
from tests.conftest import checkout_payload


def _add_product_to_cart(client, price=100, stock=10):
    product = Product.objects.create(
        name="Test Product",
        price=price,
        stock_quantity=stock,
        is_active=True,
    )
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )
    return product


# ---------------------------------------------------------------------------
# save_to_profile = True (authenticated, billing_same_as_shipping = True)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_to_profile_creates_two_addresses(auth_client, user):
    """
    First checkout with save_to_profile=True and no pre-existing profile
    defaults: both shipping and billing Address rows are created and set as
    profile defaults.
    """
    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        save_to_profile=True,
        billing_same_as_shipping=True,
    )
    resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    assert Address.objects.filter(profile__user=user).count() == 2


@pytest.mark.django_db
def test_save_to_profile_sets_profile_defaults(auth_client, user):
    """The two created addresses are set as shipping and billing defaults."""
    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        save_to_profile=True,
    )
    resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    profile = CustomerProfile.objects.get(user=user)
    assert profile.default_shipping_address is not None
    assert profile.default_billing_address is not None
    # Must be distinct rows
    assert profile.default_shipping_address_id != profile.default_billing_address_id


@pytest.mark.django_db
def test_save_to_profile_shipping_address_fields(auth_client, user):
    """The shipping Address row carries the correct field values."""
    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        save_to_profile=True,
        shipping_first_name="Jane",
        shipping_last_name="Smith",
        shipping_address_line1="123 Main St",
        shipping_address_line2="Apt 4B",
        shipping_city="Springfield",
        shipping_postal_code="12345",
        shipping_country="US",
        shipping_phone="+10000000001",
    )
    resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    profile = CustomerProfile.objects.get(user=user)
    addr = profile.default_shipping_address

    assert addr.first_name == "Jane"
    assert addr.last_name == "Smith"
    assert addr.street_line_1 == "123 Main St"
    assert addr.street_line_2 == "Apt 4B"
    assert addr.city == "Springfield"
    assert addr.postal_code == "12345"
    assert str(addr.country) == "US"
    assert addr.phone == "+10000000001"


# ---------------------------------------------------------------------------
# save_to_profile = True, billing_same_as_shipping = False
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_to_profile_separate_billing_fields(auth_client, user):
    """
    When billing_same_as_shipping=False, the billing Address row is built from
    the billing fields, not the shipping fields.
    """
    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        save_to_profile=True,
        billing_same_as_shipping=False,
        billing_first_name="Alice",
        billing_last_name="Brown",
        billing_address_line1="456 Elm St",
        billing_address_line2="",
        billing_city="Shelbyville",
        billing_postal_code="99999",
        billing_country="US",
        billing_phone="+10000000002",
    )
    resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    profile = CustomerProfile.objects.get(user=user)
    billing = profile.default_billing_address

    assert billing.first_name == "Alice"
    assert billing.last_name == "Brown"
    assert billing.street_line_1 == "456 Elm St"
    assert billing.city == "Shelbyville"
    assert billing.postal_code == "99999"


# ---------------------------------------------------------------------------
# save_to_profile = False (no addresses should be created)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_to_profile_false_does_not_create_addresses(auth_client, user):
    """save_to_profile=False must not create any Address records."""
    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        save_to_profile=False,
    )
    resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    assert Address.objects.filter(profile__user=user).count() == 0


@pytest.mark.django_db
def test_save_to_profile_omitted_does_not_create_addresses(auth_client, user):
    """When save_to_profile is absent, no addresses are created (default False)."""
    _add_product_to_cart(auth_client)

    payload = checkout_payload(customer_email=user.email)
    # Explicitly confirm save_to_profile is absent
    payload.pop("save_to_profile", None)

    resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    assert Address.objects.filter(profile__user=user).count() == 0


# ---------------------------------------------------------------------------
# Replaces existing profile defaults
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_to_profile_replaces_existing_defaults(auth_client, user):
    """
    If the user already has default addresses, they are replaced with the new
    ones created at checkout.
    """
    # Pre-create a profile with an existing address
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    old_addr = Address.objects.create(
        profile=profile,
        first_name="Old",
        last_name="Address",
        street_line_1="Old Street 1",
        city="Old City",
        postal_code="00000",
        country="US",
        phone="+10000000000",
    )
    profile.default_shipping_address = old_addr
    profile.default_billing_address = old_addr
    profile.save()

    _add_product_to_cart(auth_client)

    payload = checkout_payload(
        customer_email=user.email,
        save_to_profile=True,
        shipping_first_name="New",
        shipping_last_name="Name",
        shipping_address_line1="New Street 99",
        shipping_city="New City",
        shipping_postal_code="11111",
        shipping_country="US",
        shipping_phone="+10000000099",
    )
    resp = auth_client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    profile.refresh_from_db()
    assert profile.default_shipping_address_id != old_addr.pk
    assert profile.default_billing_address_id != old_addr.pk


# ---------------------------------------------------------------------------
# Guest checkout — save_to_profile is silently ignored
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_to_profile_ignored_for_guest(client):
    """
    Unauthenticated (guest) checkout with save_to_profile=True must succeed
    without creating any Address records and without raising errors.
    """
    product = Product.objects.create(
        name="Guest Product",
        price=50,
        stock_quantity=5,
        is_active=True,
    )
    client.get("/api/v1/cart/")
    client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 1},
        format="json",
    )

    payload = checkout_payload(
        customer_email="guest@example.com",
        save_to_profile=True,
    )
    resp = client.post("/api/v1/cart/checkout/", payload, format="json")

    assert resp.status_code == 201
    assert Address.objects.count() == 0


# ---------------------------------------------------------------------------
# No-op protection: unchanged addresses must not create new rows
# ---------------------------------------------------------------------------

def _make_matching_address(profile, **overrides):
    """
    Create an Address that matches the fields produced by the default
    checkout_payload() (i.e. shipping_first_name="E2E", shipping_last_name="Customer",
    shipping_address_line1="E2E Main Street 1", etc.).  Use *overrides* to set
    different field values.
    """
    fields = dict(
        first_name="E2E",
        last_name="Customer",
        street_line_1="E2E Main Street 1",
        street_line_2="",
        city="E2E City",
        postal_code="00000",
        country="US",
        phone="+10000000000",
    )
    fields.update(overrides)
    return Address.objects.create(profile=profile, **fields)


@pytest.mark.django_db
def test_no_op_both_sides_unchanged(auth_client, user):
    """
    When both shipping and billing defaults already match the effective
    checkout addresses, no new Address rows are created and the existing
    default references are unchanged.
    """
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    existing_ship = _make_matching_address(profile)
    # billing_same_as_shipping=True → effective billing == effective shipping
    existing_bill = _make_matching_address(profile)
    profile.default_shipping_address = existing_ship
    profile.default_billing_address = existing_bill
    profile.save()

    _add_product_to_cart(auth_client)
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email, save_to_profile=True),
        format="json",
    )

    assert resp.status_code == 201
    # No new rows
    assert Address.objects.filter(profile=profile).count() == 2
    # Default references unchanged
    profile.refresh_from_db()
    assert profile.default_shipping_address_id == existing_ship.pk
    assert profile.default_billing_address_id == existing_bill.pk


@pytest.mark.django_db
def test_no_op_shipping_changed_billing_unchanged(auth_client, user):
    """
    When shipping changes but billing is unchanged, only one new shipping row
    is created; the billing default reference is preserved.
    """
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    # Old shipping is different from what the checkout will submit
    existing_ship = _make_matching_address(profile, street_line_1="Old Street 1")
    # Billing matches "Alice Doe / 456 Billing St / ..." which we'll confirm below
    existing_bill = Address.objects.create(
        profile=profile,
        first_name="Alice",
        last_name="Doe",
        street_line_1="456 Billing St",
        street_line_2="Suite 1",
        city="Billingtown",
        postal_code="99999",
        country="US",
        phone="+19999999999",
    )
    profile.default_shipping_address = existing_ship
    profile.default_billing_address = existing_bill
    profile.save()

    initial_addr_count = Address.objects.filter(profile=profile).count()

    _add_product_to_cart(auth_client)
    # Shipping uses the default payload (different from existing_ship)
    # Billing is explicit and matches existing_bill exactly
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(
            customer_email=user.email,
            save_to_profile=True,
            billing_same_as_shipping=False,
            billing_first_name="Alice",
            billing_last_name="Doe",
            billing_address_line1="456 Billing St",
            billing_address_line2="Suite 1",
            billing_city="Billingtown",
            billing_postal_code="99999",
            billing_country="US",
            billing_phone="+19999999999",
        ),
        format="json",
    )

    assert resp.status_code == 201
    # Exactly one new row (shipping)
    assert Address.objects.filter(profile=profile).count() == initial_addr_count + 1
    profile.refresh_from_db()
    assert profile.default_shipping_address_id != existing_ship.pk
    assert profile.default_billing_address_id == existing_bill.pk


@pytest.mark.django_db
def test_no_op_billing_changed_shipping_unchanged(auth_client, user):
    """
    When billing changes but shipping is unchanged, only one new billing row
    is created; the shipping default reference is preserved.
    """
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    # Shipping matches the default checkout_payload values exactly
    existing_ship = _make_matching_address(profile)
    # Old billing is different from what the checkout will submit
    existing_bill = _make_matching_address(profile, street_line_1="Old Billing St")
    profile.default_shipping_address = existing_ship
    profile.default_billing_address = existing_bill
    profile.save()

    initial_addr_count = Address.objects.filter(profile=profile).count()

    _add_product_to_cart(auth_client)
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(
            customer_email=user.email,
            save_to_profile=True,
            # Shipping intentionally left as defaults (matches existing_ship)
            billing_same_as_shipping=False,
            billing_first_name="Bob",
            billing_last_name="Smith",
            billing_address_line1="789 New Billing Ave",
            billing_address_line2="",
            billing_city="Newtown",
            billing_postal_code="11111",
            billing_country="US",
            billing_phone="+10000000099",
        ),
        format="json",
    )

    assert resp.status_code == 201
    # Exactly one new row (billing)
    assert Address.objects.filter(profile=profile).count() == initial_addr_count + 1
    profile.refresh_from_db()
    assert profile.default_shipping_address_id == existing_ship.pk
    assert profile.default_billing_address_id != existing_bill.pk


@pytest.mark.django_db
def test_no_op_both_changed(auth_client, user):
    """
    When both shipping and billing differ from the current defaults, two new
    rows are created and both defaults are repointed.
    """
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    existing_ship = _make_matching_address(profile, street_line_1="Old Ship St")
    existing_bill = _make_matching_address(profile, street_line_1="Old Bill St")
    profile.default_shipping_address = existing_ship
    profile.default_billing_address = existing_bill
    profile.save()

    initial_addr_count = Address.objects.filter(profile=profile).count()

    _add_product_to_cart(auth_client)
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(
            customer_email=user.email,
            save_to_profile=True,
            # Default shipping (different from "Old Ship St")
            billing_same_as_shipping=False,
            billing_first_name="Carol",
            billing_last_name="White",
            billing_address_line1="321 Different Ave",
            billing_address_line2="",
            billing_city="Diffton",
            billing_postal_code="22222",
            billing_country="US",
            billing_phone="+10000000088",
        ),
        format="json",
    )

    assert resp.status_code == 201
    assert Address.objects.filter(profile=profile).count() == initial_addr_count + 2
    profile.refresh_from_db()
    assert profile.default_shipping_address_id != existing_ship.pk
    assert profile.default_billing_address_id != existing_bill.pk


@pytest.mark.django_db
def test_no_op_checkout_failure_leaves_profile_unchanged(auth_client, user):
    """
    When checkout fails (empty cart), the profile is not modified at all.
    """
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    existing_ship = _make_matching_address(profile)
    existing_bill = _make_matching_address(profile)
    profile.default_shipping_address = existing_ship
    profile.default_billing_address = existing_bill
    profile.save()

    initial_addr_count = Address.objects.filter(profile=profile).count()

    # Do NOT add any product — checkout will fail with 400 CART_EMPTY
    auth_client.get("/api/v1/cart/")
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email, save_to_profile=True),
        format="json",
    )

    assert resp.status_code == 400
    assert Address.objects.filter(profile=profile).count() == initial_addr_count
    profile.refresh_from_db()
    assert profile.default_shipping_address_id == existing_ship.pk
    assert profile.default_billing_address_id == existing_bill.pk


@pytest.mark.django_db
def test_no_op_whitespace_normalization(auth_client, user):
    """
    Harmless leading/trailing whitespace in persisted address fields is
    normalized before comparison, so no spurious new row is created.
    """
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    # Manually store an address with extra whitespace in text fields
    existing_ship = Address.objects.create(
        profile=profile,
        first_name="  E2E  ",
        last_name="  Customer  ",
        street_line_1="  E2E Main Street 1  ",
        street_line_2="  ",
        city="  E2E City  ",
        postal_code="  00000  ",
        country="US",
        phone="  +10000000000  ",
    )
    existing_bill = Address.objects.create(
        profile=profile,
        first_name="  E2E  ",
        last_name="  Customer  ",
        street_line_1="  E2E Main Street 1  ",
        street_line_2="  ",
        city="  E2E City  ",
        postal_code="  00000  ",
        country="US",
        phone="  +10000000000  ",
    )
    profile.default_shipping_address = existing_ship
    profile.default_billing_address = existing_bill
    profile.save()

    _add_product_to_cart(auth_client)
    resp = auth_client.post(
        "/api/v1/cart/checkout/",
        checkout_payload(customer_email=user.email, save_to_profile=True),
        format="json",
    )

    assert resp.status_code == 201
    # No new rows despite whitespace difference in stored values
    assert Address.objects.filter(profile=profile).count() == 2
    profile.refresh_from_db()
    assert profile.default_shipping_address_id == existing_ship.pk
    assert profile.default_billing_address_id == existing_bill.pk
