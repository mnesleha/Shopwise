import pytest

from auditlog.models import AuditEvent
from auditlog.actions import AuditActions
from orders.models import Order


pytestmark = pytest.mark.django_db


def _make_staff(user):
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


def test_admin_deliver_emits_audit_event(auth_client, user, order_factory):
    _make_staff(user)
    order = order_factory(user=user, status=Order.Status.SHIPPED)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/deliver/", format="json")
    assert resp.status_code == 200

    ev = (
        AuditEvent.objects.filter(entity_type="order", entity_id=str(
            order.id), action=AuditActions.ORDER_DELIVERED)
        .order_by("-created_at")
        .first()
    )
    assert ev is not None


def test_admin_cancel_emits_audit_event(auth_client, user, order_factory):
    _make_staff(user)
    order = order_factory(user=user, status=Order.Status.CREATED)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/cancel/", format="json")
    assert resp.status_code == 200

    ev = (
        AuditEvent.objects.filter(entity_type="order", entity_id=str(
            order.id), action=AuditActions.ORDER_CANCELLED_ADMIN)
        .order_by("-created_at")
        .first()
    )
    assert ev is not None
