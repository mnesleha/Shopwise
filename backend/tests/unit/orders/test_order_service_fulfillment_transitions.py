import pytest

from auditlog.models import AuditEvent
from auditlog.actions import AuditActions
from orders.models import Order
from orders.services.order_service import OrderService
from api.exceptions.orders import InvalidOrderStateException


@pytest.mark.django_db
def test_ship_by_admin_transitions_paid_to_shipped_and_emits_audit(user, order_factory):
    order = order_factory(user=user, status=Order.Status.PAID)

    OrderService.ship_by_admin(order=order, actor_user=user)

    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED

    ev = AuditEvent.objects.filter(entity_id=str(
        order.id)).order_by("-created_at").first()
    assert ev is not None
    assert ev.entity_type == "order"
    assert ev.action == AuditActions.ORDER_SHIPPED
    assert ev.actor_type == AuditEvent.ActorType.ADMIN


@pytest.mark.django_db
def test_ship_by_admin_invalid_states_raise_409(user, order_factory):
    order = order_factory(user=user, status=Order.Status.CREATED)

    with pytest.raises(InvalidOrderStateException):
        OrderService.ship_by_admin(order=order, actor_user=user)


@pytest.mark.django_db
def test_deliver_by_admin_transitions_shipped_to_delivered_and_emits_audit(user, order_factory):
    order = order_factory(user=user, status=Order.Status.SHIPPED)

    OrderService.deliver_by_admin(order=order, actor_user=user)

    order.refresh_from_db()
    assert order.status == Order.Status.DELIVERED

    ev = AuditEvent.objects.filter(entity_id=str(
        order.id)).order_by("-created_at").first()
    assert ev is not None
    assert ev.entity_type == "order"
    assert ev.action == AuditActions.ORDER_DELIVERED
    assert ev.actor_type == AuditEvent.ActorType.ADMIN


@pytest.mark.django_db
def test_deliver_by_admin_invalid_states_raise_409(user, order_factory):
    order = order_factory(user=user, status=Order.Status.PAID)

    with pytest.raises(InvalidOrderStateException):
        OrderService.deliver_by_admin(order=order, actor_user=user)


@pytest.mark.django_db
def test_cancel_by_admin_transitions_created_to_cancelled_and_emits_audit(user, order_factory):
    order = order_factory(user=user, status=Order.Status.CREATED)

    OrderService.cancel_by_admin(order=order, actor_user=user)

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.cancelled_by == Order.CancelledBy.ADMIN
    assert order.cancel_reason == Order.CancelReason.ADMIN_CANCELLED

    ev = AuditEvent.objects.filter(entity_id=str(
        order.id)).order_by("-created_at").first()
    assert ev is not None
    assert ev.entity_type == "order"
    assert ev.action == AuditActions.ORDER_CANCELLED_ADMIN
    assert ev.actor_type == AuditEvent.ActorType.ADMIN


@pytest.mark.django_db
def test_cancel_by_admin_allows_payment_failed(user, order_factory):
    order = order_factory(user=user, status=Order.Status.PAYMENT_FAILED)

    OrderService.cancel_by_admin(order=order, actor_user=user)

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.cancelled_by == Order.CancelledBy.ADMIN
    assert order.cancel_reason == Order.CancelReason.ADMIN_CANCELLED


@pytest.mark.django_db
def test_cancel_by_admin_not_allowed_for_paid(user, order_factory):
    order = order_factory(user=user, status=Order.Status.PAID)

    with pytest.raises(InvalidOrderStateException):
        OrderService.cancel_by_admin(order=order, actor_user=user)
