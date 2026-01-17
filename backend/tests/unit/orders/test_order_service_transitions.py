import pytest

from payments.models import Payment
from orders.models import Order

from api.exceptions.payment import PaymentAlreadyExistsException, OrderNotPayableException
from api.exceptions.orders import InvalidOrderStateException

from orders.services.order_service import OrderService


@pytest.mark.django_db
def test_create_payment_success_transitions_created_to_paid_and_creates_payment(user, order_factory):
    # Arrange
    order = order_factory(user=user, status=Order.Status.CREATED)

    # Act
    payment = OrderService.create_payment_and_apply_result(
        order=order,
        result="success",
        actor_user=user,
    )

    # Assert
    order.refresh_from_db()
    payment.refresh_from_db()
    assert payment.order_id == order.id
    assert payment.status == Payment.Status.SUCCESS
    assert order.status == Order.Status.PAID


@pytest.mark.django_db
def test_create_payment_fail_transitions_created_to_payment_failed_and_creates_payment(user, order_factory):
    order = order_factory(user=user, status=Order.Status.CREATED)

    payment = OrderService.create_payment_and_apply_result(
        order=order,
        result="fail",
        actor_user=user,
    )

    order.refresh_from_db()
    payment.refresh_from_db()
    assert payment.status == Payment.Status.FAILED
    assert order.status == Order.Status.PAYMENT_FAILED


@pytest.mark.django_db
def test_create_payment_raises_if_payment_already_exists(user, order_factory):
    order = order_factory(user=user, status=Order.Status.CREATED)
    Payment.objects.create(order=order, status=Payment.Status.SUCCESS)

    with pytest.raises(PaymentAlreadyExistsException):
        OrderService.create_payment_and_apply_result(
            order=order,
            result="success",
            actor_user=user,
        )


@pytest.mark.django_db
def test_create_payment_raises_if_order_not_payable(user, order_factory):
    order = order_factory(user=user, status=Order.Status.PAID)

    with pytest.raises(OrderNotPayableException):
        OrderService.create_payment_and_apply_result(
            order=order,
            result="success",
            actor_user=user,
        )


@pytest.mark.django_db
def test_cancel_by_customer_transitions_created_to_cancelled(user, order_factory):
    order = order_factory(user=user, status=Order.Status.CREATED)

    OrderService.cancel_by_customer(order=order, actor_user=user)

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.cancel_reason == Order.CancelReason.CUSTOMER_REQUEST
    assert order.cancelled_by == Order.CancelledBy.CUSTOMER
    assert order.cancelled_at is not None


@pytest.mark.django_db
def test_cancel_by_customer_raises_if_invalid_state(user, order_factory):
    order = order_factory(user=user, status=Order.Status.PAID)

    with pytest.raises(InvalidOrderStateException):
        OrderService.cancel_by_customer(order=order, actor_user=user)
