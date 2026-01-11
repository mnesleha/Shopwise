import pytest
from django.contrib.auth import get_user_model

from orders.services.claim import claim_guest_orders_for_user
from orders.models import Order


@pytest.fixture
def minimal_order_kwargs():
    return {
        "customer_email": "customer@example.com",
        "shipping_name": "E2E Customer",
        "shipping_address_line1": "E2E Main Street 1",
        "shipping_address_line2": "",
        "shipping_city": "E2E City",
        "shipping_postal_code": "00000",
        "shipping_country": "US",
        "shipping_phone": "+10000000000",
        "billing_same_as_shipping": True,
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_claim_is_idempotent_under_repeated_calls_mysql(minimal_order_kwargs):
    """
    MySQL suite: deterministic idempotence.
    Repeated claims must not flip state or claim twice.
    """
    User = get_user_model()
    user = User.objects.create_user(
        email="customer@example.com", password="Passw0rd!123")
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    guest = Order.objects.create(user=None, **minimal_order_kwargs)

    first = claim_guest_orders_for_user(user)
    second = claim_guest_orders_for_user(user)

    assert first == 1
    assert second == 0

    guest.refresh_from_db()
    assert guest.user_id == user.id
    assert guest.is_claimed is True
    assert guest.claimed_by_user_id == user.id
    assert guest.claimed_at is not None


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql
def test_claim_only_updates_rows_matching_filters_mysql(minimal_order_kwargs):
    """
    MySQL suite: enforce the eligibility filters are DB-correct.
    """
    User = get_user_model()
    user = User.objects.create_user(
        email="customer@example.com", password="Passw0rd!123")
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    # eligible
    eligible = Order.objects.create(user=None, **minimal_order_kwargs)

    # non-eligible: different email
    other = dict(minimal_order_kwargs)
    other["customer_email"] = "other@example.com"
    nonmatch = Order.objects.create(user=None, **other)

    # non-eligible: already has user
    owned = Order.objects.create(user=user, **minimal_order_kwargs)

    claimed = claim_guest_orders_for_user(user)
    assert claimed == 1

    eligible.refresh_from_db()
    assert eligible.is_claimed is True
    assert eligible.user_id == user.id

    nonmatch.refresh_from_db()
    assert nonmatch.is_claimed is False
    assert nonmatch.user_id is None

    owned.refresh_from_db()
    assert owned.is_claimed is False
    assert owned.user_id == user.id
