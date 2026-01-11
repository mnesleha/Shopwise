import pytest
from django.contrib.auth import get_user_model

from orders.models import Order
from orders.services.claim import claim_guest_orders_for_user


@pytest.fixture
def make_user(db):
    User = get_user_model()

    def _make_user(*, email: str, verified: bool) -> object:
        u = User.objects.create_user(email=email, password="Passw0rd!123")
        u.email_verified = verified
        u.save(update_fields=["email_verified"])
        return u

    return _make_user


@pytest.fixture
def minimal_order_kwargs():
    """
    Minimal valid Order snapshots (business contract).
    Keep deterministic (no random).
    """
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


@pytest.fixture
def make_guest_order(db, minimal_order_kwargs):
    def _make_guest_order(*, email: str, **overrides) -> Order:
        data = dict(minimal_order_kwargs)
        data["customer_email"] = email
        data.update(overrides)
        return Order.objects.create(user=None, **data)

    return _make_guest_order


@pytest.mark.django_db
def test_claim_does_nothing_when_user_not_verified(make_user, make_guest_order):
    """
    Business: guest order claiming must NOT happen unless user.email_verified is True.
    """
    user = make_user(email="Customer@Example.com", verified=False)

    o1 = make_guest_order(email="customer@example.com")
    assert o1.user_id is None
    assert o1.is_claimed is False

    claimed_count = claim_guest_orders_for_user(user)

    assert claimed_count == 0

    o1.refresh_from_db()
    assert o1.user_id is None
    assert o1.is_claimed is False
    assert o1.claimed_at is None
    assert o1.claimed_by_user_id is None


@pytest.mark.django_db
def test_claim_claims_only_matching_unowned_orders(make_user, make_guest_order):
    """
    Business_toggle:
    - eligible only if order.user is NULL
    - and email matches customer_email_normalized == user.email normalized
    - and user.email_verified == True
    """
    user = make_user(email="Customer@Example.com", verified=True)

    o_match_1 = make_guest_order(email="customer@example.com")
    o_match_2 = make_guest_order(email="  CUSTOMER@example.com  ")
    o_other = make_guest_order(email="other@example.com")

    # already-owned should not be claimed
    owned = make_guest_order(email="customer@example.com")
    owned.user_id = user.id
    owned.save()

    claimed_count = claim_guest_orders_for_user(user)
    assert claimed_count == 2

    for o in (o_match_1, o_match_2):
        o.refresh_from_db()
        assert o.user_id == user.id
        assert o.is_claimed is True
        assert o.claimed_at is not None
        assert o.claimed_by_user_id == user.id

    o_other.refresh_from_db()
    assert o_other.user_id is None
    assert o_other.is_claimed is False

    owned.refresh_from_db()
    assert owned.user_id == user.id
    # depending on your rules, owned may or may not be marked claimed; we assert it was not processed
    # because it's not guest (user != NULL)
    assert owned.is_claimed is False


@pytest.mark.django_db
def test_claim_is_idempotent(make_user, make_guest_order):
    user = make_user(email="customer@example.com", verified=True)

    o1 = make_guest_order(email="customer@example.com")

    first = claim_guest_orders_for_user(user)
    second = claim_guest_orders_for_user(user)

    assert first == 1
    assert second == 0

    o1.refresh_from_db()
    assert o1.user_id == user.id
    assert o1.is_claimed is True
    assert o1.claimed_at is not None
    assert o1.claimed_by_user_id == user.id


@pytest.mark.django_db
def test_claim_does_not_touch_non_guest_orders(make_user, make_guest_order, minimal_order_kwargs):
    user = make_user(email="customer@example.com", verified=True)

    # create a non-guest order (user set) with same email - must not be reprocessed
    owned = Order.objects.create(user=user, **minimal_order_kwargs)
    assert owned.user_id == user.id

    claimed_count = claim_guest_orders_for_user(user)
    assert claimed_count == 0

    owned.refresh_from_db()
    assert owned.user_id == user.id
    assert owned.is_claimed is False
