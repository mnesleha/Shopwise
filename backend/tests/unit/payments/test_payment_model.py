from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from orders.services.order_service import OrderService
from payments.models import Payment
from tests.conftest import create_valid_order

User = get_user_model()

# ---------------------------------------------------------------------------
# Original tests — preserved unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_payment_created_with_default_status():
    user = User.objects.create_user(email="payuser1@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(order=order)

    assert payment.status == Payment.Status.PENDING


@pytest.mark.django_db
def test_payment_must_have_order():
    payment = Payment(order=None)

    with pytest.raises(ValidationError):
        payment.full_clean()


@pytest.mark.django_db
def test_payment_invalid_status_is_rejected():
    user = User.objects.create_user(email="payuser2@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment(order=order, status="INVALID")

    with pytest.raises(ValidationError):
        payment.full_clean()


@pytest.mark.django_db
def test_valid_payment_is_valid():
    user = User.objects.create_user(email="payuser3@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment(order=order, status=Payment.Status.PENDING)

    payment.full_clean()  # should not raise


# ---------------------------------------------------------------------------
# New tests — Payment domain model expansion
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_payment_stores_payment_method_and_provider_separately():
    """Payment can store business-facing method and technical provider independently."""
    user = User.objects.create_user(email="payuser10@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(
        order=order,
        payment_method=Payment.PaymentMethod.CARD,
        provider=Payment.Provider.DEV_FAKE,
    )

    assert payment.payment_method == Payment.PaymentMethod.CARD
    assert payment.provider == Payment.Provider.DEV_FAKE


@pytest.mark.django_db
def test_payment_provider_defaults_to_dev_fake():
    """Provider defaults to DEV_FAKE when not specified."""
    user = User.objects.create_user(email="payuser11@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(order=order)

    assert payment.provider == Payment.Provider.DEV_FAKE


@pytest.mark.django_db
def test_payment_payment_method_is_nullable():
    """payment_method is nullable for backward compatibility with existing records."""
    user = User.objects.create_user(email="payuser12@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(order=order)

    assert payment.payment_method is None


@pytest.mark.django_db
def test_payment_stores_provider_metadata():
    """Payment can store provider metadata required for future external gateway."""
    user = User.objects.create_user(email="payuser13@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(
        order=order,
        provider_payment_id="ext-pay-abc123",
        provider_reference="internal-ref-xyz",
    )

    assert payment.provider_payment_id == "ext-pay-abc123"
    assert payment.provider_reference == "internal-ref-xyz"


@pytest.mark.django_db
def test_payment_stores_amount_and_currency_snapshot():
    """Payment can snapshot the amount and currency at payment time."""
    user = User.objects.create_user(email="payuser14@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(
        order=order,
        amount=Decimal("99.99"),
        currency="EUR",
    )

    assert payment.amount == Decimal("99.99")
    assert payment.currency == "EUR"


@pytest.mark.django_db
def test_payment_paid_at_and_failed_at_default_to_null():
    """paid_at and failed_at are null by default."""
    user = User.objects.create_user(email="payuser15@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(order=order, status=Payment.Status.PENDING)

    assert payment.paid_at is None
    assert payment.failed_at is None


@pytest.mark.django_db
def test_payment_paid_at_is_set_on_success():
    """paid_at is populated when a payment succeeds via OrderService."""
    user = User.objects.create_user(email="payuser16@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = OrderService.create_payment_and_apply_result(
        order=order, result="success", actor_user=user
    )

    assert payment.paid_at is not None
    assert payment.failed_at is None


@pytest.mark.django_db
def test_payment_failed_at_and_failure_reason_set_on_failure():
    """failed_at and failure_reason are set when a payment fails via OrderService."""
    user = User.objects.create_user(email="payuser17@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = OrderService.create_payment_and_apply_result(
        order=order, result="fail", actor_user=user
    )

    assert payment.failed_at is not None
    assert payment.failure_reason is not None
    assert payment.paid_at is None


@pytest.mark.django_db
def test_dev_fake_flow_sets_provider_field():
    """The existing DEV_FAKE flow sets the provider field on the created payment."""
    user = User.objects.create_user(email="payuser18@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = OrderService.create_payment_and_apply_result(
        order=order, result="success", actor_user=user
    )

    assert payment.provider == Payment.Provider.DEV_FAKE


@pytest.mark.django_db
def test_payment_invalid_provider_is_rejected():
    """An unrecognised provider value is rejected by full_clean()."""
    user = User.objects.create_user(email="payuser19@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment(order=order, provider="NONEXISTENT_PROVIDER")

    with pytest.raises(ValidationError):
        payment.full_clean()


@pytest.mark.django_db
def test_payment_invalid_payment_method_is_rejected():
    """An unrecognised payment_method value is rejected by full_clean()."""
    user = User.objects.create_user(email="payuser20@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment(order=order, payment_method="BITCOIN")

    with pytest.raises(ValidationError):
        payment.full_clean()


@pytest.mark.django_db
def test_payment_str_representation():
    """__str__ includes the pk and status."""
    user = User.objects.create_user(email="payuser21@example.com", password="pass")
    order = create_valid_order(user=user)

    payment = Payment.objects.create(order=order, status=Payment.Status.PENDING)

    assert str(payment.pk) in str(payment)
    assert "PENDING" in str(payment)
