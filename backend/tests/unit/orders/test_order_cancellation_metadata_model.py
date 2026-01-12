import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from conftest import create_valid_order
from orders.models import Order


@pytest.mark.django_db
def test_order_cancellation_metadata_can_be_empty():
    """
    Cancellation metadata must be optional (nullable/blank),
    because most orders are not cancelled.
    """
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    order.cancel_reason = None
    order.cancelled_by = None
    order.cancelled_at = None

    # Should not raise
    order.full_clean()
    order.save()

    order.refresh_from_db()
    assert order.cancel_reason is None
    assert order.cancelled_by is None
    assert order.cancelled_at is None


@pytest.mark.django_db
def test_order_cancel_reason_accepts_only_known_values():
    """
    cancel_reason must be limited to TextChoices values.
    """
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    order.cancel_reason = "NOT_A_VALID_REASON"

    with pytest.raises(ValidationError) as e:
        order.full_clean()

    assert "cancel_reason" in e.value.message_dict


@pytest.mark.django_db
def test_order_cancelled_by_accepts_only_known_values():
    """
    cancelled_by must be limited to TextChoices values.
    """
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    order.cancelled_by = "HACKER"

    with pytest.raises(ValidationError) as e:
        order.full_clean()

    assert "cancelled_by" in e.value.message_dict


@pytest.mark.django_db
def test_order_cancelled_at_can_be_set():
    order = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    order.cancel_reason = Order.CancelReason.CUSTOMER_REQUEST
    order.cancelled_by = Order.CancelledBy.CUSTOMER
    order.cancelled_at = timezone.now()

    # Should not raise
    order.full_clean()
    order.save()

    order.refresh_from_db()
    assert order.cancel_reason == Order.CancelReason.CUSTOMER_REQUEST
    assert order.cancelled_by == Order.CancelledBy.CUSTOMER
    assert order.cancelled_at is not None


@pytest.mark.django_db
def test_order_cancellation_choices_include_expected_values():
    """
    Smoke test to ensure the expected enum values exist.
    (Prevents accidental renames that would break API/service layer later.)
    """
    _ = create_valid_order(
        user=None, status=Order.Status.CREATED, customer_email="guest@example.com")

    assert Order.CancelReason.CUSTOMER_REQUEST
    assert Order.CancelReason.PAYMENT_FAILED
    assert Order.CancelReason.PAYMENT_EXPIRED
    assert Order.CancelReason.OUT_OF_STOCK
    assert Order.CancelReason.SHOP_REQUEST
    assert Order.CancelReason.FRAUD_SUSPECTED

    assert Order.CancelledBy.CUSTOMER
    assert Order.CancelledBy.ADMIN
    assert Order.CancelledBy.SYSTEM
