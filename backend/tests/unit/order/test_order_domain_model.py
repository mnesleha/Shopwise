import pytest
from django.core.exceptions import ValidationError
from orders.models import Order
from django.contrib.auth import get_user_model
from django.utils import timezone


@pytest.fixture
def valid_order_kwargs():
    return {
        "customer_email": "customer@example.com",
        "shipping_name": "John Doe",
        "shipping_address_line1": "123 Main St",
        "shipping_address_line2": "",
        "shipping_city": "Chicago",
        "shipping_postal_code": "60601",
        "shipping_country": "US",
        "shipping_phone": "+14155552671",
        "billing_same_as_shipping": True,
    }


def build_order_kwargs(**overrides):
    data = {
        "customer_email": "guest@example.com",
        "shipping_name": "Guest User",
        "shipping_address_line1": "123 Main St",
        "shipping_city": "Prague",
        "shipping_postal_code": "11000",
        "shipping_country": "CZ",
        "shipping_phone": "+420123456789",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_order_requires_customer_email_and_normalizes_it(valid_order_kwargs):
    o = Order(**{**valid_order_kwargs,
              "customer_email": "  Customer@Example.COM  "})
    o.save()
    assert o.customer_email_normalized == "customer@example.com"


@pytest.mark.django_db
def test_guest_order_is_allowed_when_required_shipping_snapshots_present():
    order = Order(user=None, **build_order_kwargs())

    order.full_clean()
    order.save()

    assert order.pk is not None


@pytest.mark.django_db
def test_order_requires_shipping_snapshots():
    order = Order(**build_order_kwargs(shipping_city=None))

    with pytest.raises(ValidationError) as exc:
        order.full_clean()

    assert "shipping_city" in exc.value.message_dict


@pytest.mark.django_db
def test_billing_is_optional_when_same_as_shipping_true():
    order = Order(**build_order_kwargs(billing_same_as_shipping=True))

    order.full_clean()
    order.save()

    assert order.pk is not None


@pytest.mark.django_db
def test_billing_is_required_when_same_as_shipping_false():
    order = Order(**build_order_kwargs(billing_same_as_shipping=False))

    with pytest.raises(ValidationError) as exc:
        order.full_clean()

    errors = exc.value.message_dict
    assert "billing_name" in errors
    assert "billing_address_line1" in errors
    assert "billing_city" in errors
    assert "billing_postal_code" in errors
    assert "billing_country" in errors


@pytest.mark.django_db
def test_claim_fields_default_to_unclaimed_state():
    order = Order(**build_order_kwargs())

    order.full_clean()
    order.save()

    order.refresh_from_db()
    assert order.is_claimed is False
    assert order.claimed_at is None
    assert order.claimed_by_user is None


@pytest.mark.django_db
def test_order_rejects_blank_customer_email_after_stripping(valid_order_kwargs):
    o = Order(**{**valid_order_kwargs, "customer_email": "   "})
    with pytest.raises(ValidationError) as exc:
        o.full_clean()
    assert "customer_email" in exc.value.message_dict


@pytest.mark.django_db
def test_order_rejects_invalid_customer_email_format(valid_order_kwargs):
    o = Order(**{**valid_order_kwargs, "customer_email": "not-an-email"})
    with pytest.raises(ValidationError) as exc:
        o.full_clean()
    assert "customer_email" in exc.value.message_dict


@pytest.mark.django_db
def test_order_rejects_null_customer_email(valid_order_kwargs):
    o = Order(**{**valid_order_kwargs, "customer_email": None})
    with pytest.raises(ValidationError) as exc:
        o.full_clean()
    assert "customer_email" in exc.value.message_dict


REQUIRED_SHIPPING_FIELDS = [
    "shipping_name",
    "shipping_address_line1",
    "shipping_city",
    "shipping_postal_code",
    "shipping_country",
    "shipping_phone",
]


@pytest.mark.django_db
@pytest.mark.parametrize("missing_field", REQUIRED_SHIPPING_FIELDS)
def test_order_requires_each_shipping_required_field(valid_order_kwargs, missing_field):
    data = dict(valid_order_kwargs)
    data[missing_field] = ""
    o = Order(**data)
    with pytest.raises(ValidationError) as exc:
        o.full_clean()
    assert missing_field in exc.value.message_dict


@pytest.mark.django_db
def test_billing_is_optional_when_same_as_shipping_true(valid_order_kwargs):
    o = Order(**valid_order_kwargs)
    o.save()
    assert o.billing_same_as_shipping is True


@pytest.mark.django_db
def test_billing_is_required_when_same_as_shipping_false(valid_order_kwargs):
    data = dict(valid_order_kwargs)
    data["billing_same_as_shipping"] = False
    o = Order(**data)
    with pytest.raises(ValidationError) as exc:
        o.full_clean()
    for f in ["billing_name", "billing_address_line1", "billing_city", "billing_postal_code", "billing_country"]:
        assert f in exc.value.message_dict


@pytest.mark.django_db
def test_billing_separate_succeeds_when_required_fields_present(valid_order_kwargs):
    data = dict(valid_order_kwargs)
    data["billing_same_as_shipping"] = False
    data.update({
        "billing_name": "Jane Billing",
        "billing_address_line1": "456 Billing Rd",
        "billing_city": "Chicago",
        "billing_postal_code": "60602",
        "billing_country": "US",
        # billing_phone optional
    })
    o = Order(**data)
    o.save()
    assert o.billing_same_as_shipping is False
    assert o.billing_name == "Jane Billing"


@pytest.mark.django_db
def test_claim_fields_default_to_unclaimed_state(valid_order_kwargs):
    o = Order(**valid_order_kwargs)
    o.save()
    assert o.is_claimed is False
    assert o.claimed_at is None
    assert o.claimed_by_user_id is None


@pytest.mark.django_db
def test_claim_invariants_require_metadata_when_claimed(valid_order_kwargs):
    User = get_user_model()
    u = User.objects.create_user(
        email="v@example.com", password="Passw0rd!123")
    o = Order(**valid_order_kwargs)
    o.is_claimed = True
    o.user = u
    # missing claimed_at / claimed_by_user => invalid
    with pytest.raises(ValidationError) as exc:
        o.full_clean()
    assert "claimed_at" in exc.value.message_dict or "claimed_by_user" in exc.value.message_dict


@pytest.mark.django_db
def test_claim_invariants_allow_consistent_claim_state(valid_order_kwargs):
    User = get_user_model()
    u = User.objects.create_user(
        email="v2@example.com", password="Passw0rd!123")
    o = Order(**valid_order_kwargs)
    o.user = u
    o.is_claimed = True
    o.claimed_by_user = u
    o.claimed_at = timezone.now()
    o.save()
    assert o.is_claimed is True


@pytest.mark.django_db
def test_claim_invariants_forbid_metadata_when_unclaimed(valid_order_kwargs):
    User = get_user_model()
    u = User.objects.create_user(
        email="v3@example.com", password="Passw0rd!123")
    o = Order(**valid_order_kwargs)
    o.user = u
    o.is_claimed = False
    o.claimed_by_user = u
    with pytest.raises(ValidationError) as exc:
        o.full_clean()
    assert "claimed_by_user" in exc.value.message_dict
