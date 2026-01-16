import pytest

from orders.models import Order
from auditlog.models import AuditEvent
from auditlog.actions import AuditAction
from auditlog.actors import ActorType


@pytest.mark.django_db
def test_customer_cancel_emits_audit_event(auth_client, order):
    # Preconditions
    assert order.status == Order.Status.CREATED

    # Act
    resp = auth_client.post(
        f"/api/v1/orders/{order.id}/cancel/", format="json")
    assert resp.status_code == 200, resp.content

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED

    # Assert audit
    ev = AuditEvent.objects.filter(
        entity_type="order",
        entity_id=str(order.id),
        action=AuditAction.ORDER_CANCELLED,
    ).order_by("-created_at").first()

    assert ev is not None
    assert ev.actor_type == ActorType.CUSTOMER
    assert ev.actor_user_id == order.user_id
    assert ev.metadata.get("cancel_reason") == order.cancel_reason
    assert ev.metadata.get("cancelled_by") == order.cancelled_by
