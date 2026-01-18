import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from orders.models import Order
from auditlog.models import AuditEvent
from auditlog.actions import AuditActions


def _make_staff(user):
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


def _grant_perm(user, perm_codename: str):
    ct = ContentType.objects.get_for_model(Order)
    perm = Permission.objects.get(content_type=ct, codename=perm_codename)
    user.user_permissions.add(perm)


@pytest.mark.django_db
def test_admin_ship_endpoint_requires_auth(client):
    resp = client.post("/api/v1/admin/orders/1/ship/", format="json")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_ship_endpoint_staff_can_ship(auth_client, user, order_factory):
    _make_staff(user)
    order = order_factory(user=user, status=Order.Status.PAID)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/ship/", format="json")
    assert resp.status_code == 200, resp.content

    order.refresh_from_db()
    assert order.status == Order.Status.SHIPPED


@pytest.mark.django_db
def test_admin_deliver_endpoint_staff_can_deliver(auth_client, user, order_factory):
    _make_staff(user)
    order = order_factory(user=user, status=Order.Status.SHIPPED)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/deliver/", format="json")
    assert resp.status_code == 200, resp.content

    order.refresh_from_db()
    assert order.status == Order.Status.DELIVERED


@pytest.mark.django_db
def test_admin_cancel_endpoint_staff_can_cancel_created(auth_client, user, order_factory):
    _make_staff(user)
    order = order_factory(user=user, status=Order.Status.CREATED)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/cancel/", format="json")
    assert resp.status_code == 200, resp.content

    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.cancel_reason == Order.CancelReason.ADMIN_CANCELLED


@pytest.mark.django_db
def test_admin_cancel_endpoint_paid_is_invalid_state_returns_409(auth_client, user, order_factory):
    _make_staff(user)
    order = order_factory(user=user, status=Order.Status.PAID)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/cancel/", format="json")
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_ORDER_STATE"


@pytest.mark.django_db
def test_admin_ship_emits_audit_event(auth_client, user, order_factory):
    _make_staff(user)
    order = order_factory(user=user, status=Order.Status.PAID)

    resp = auth_client.post(
        f"/api/v1/admin/orders/{order.id}/ship/", format="json")
    assert resp.status_code == 200

    ev = AuditEvent.objects.filter(entity_id=str(
        order.id), action=AuditActions.ORDER_SHIPPED).first()
    assert ev is not None
