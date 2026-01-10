import pytest
from django.core.exceptions import ValidationError

from orders.models import Order


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
def test_order_requires_customer_email_and_normalizes_it():
    order = Order(**build_order_kwargs(customer_email="  MiXeD@Example.COM  "))

    order.full_clean()
    order.save()

    order.refresh_from_db()
    assert order.customer_email_normalized == "mixed@example.com"


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
