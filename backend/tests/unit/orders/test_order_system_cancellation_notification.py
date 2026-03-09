"""Tests for the order system-cancellation notification triggered by overdue
reservation expiration.

Covers:
A) When overdue reservation expiration causes a system cancellation, the
   customer notification is enqueued.
B) When there are no overdue reservations, no notification is enqueued.
C) A failure inside enqueue_best_effort does not break the expiration flow.
D) The renderer produces the expected subject / body content.

The tests follow the existing ``transaction.on_commit`` interception pattern
used by ``test_guest_order_enqueue.py``.  Business-logic correctness of
``expire_overdue_reservations`` itself is covered by the existing service
unit tests.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone

from notifications.renderers import render_order_system_cancelled_notification
from orders.models import InventoryReservation, Order
from orders.services.inventory_reservation_service import expire_overdue_reservations
from products.models import Product

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_order(customer_email: str, status=Order.Status.CREATED) -> Order:
    """Create a minimal valid Order for use in these tests."""
    return Order.objects.create(
        user=None,
        status=status,
        customer_email=customer_email,
        shipping_name="Test Customer",
        shipping_address_line1="123 Test St",
        shipping_city="Test City",
        shipping_postal_code="00000",
        shipping_country="US",
        shipping_phone="+10000000000",
        billing_same_as_shipping=True,
    )


def _capture_on_commit(monkeypatch):
    """Replace transaction.on_commit with a collector; return the list."""
    callbacks = []

    def fake_on_commit(func, using=None):
        callbacks.append(func)

    monkeypatch.setattr(transaction, "on_commit", fake_on_commit)
    return callbacks


def _create_overdue_reservation(order, product, *, minutes_overdue=10):
    return InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=timezone.now() - timedelta(minutes=minutes_overdue),
    )


# ---------------------------------------------------------------------------
# A) System cancellation → notification enqueued
# ---------------------------------------------------------------------------


def test_notification_enqueued_on_system_cancellation(monkeypatch):
    """When expiration causes a system order cancellation, the customer
    notification job is enqueued via on_commit."""
    callbacks = _capture_on_commit(monkeypatch)

    product = Product.objects.create(
        name="PROD_NOTIF_A", price="10.00", stock_quantity=5, is_active=True
    )
    order = _make_order("customer@example.com")
    _create_overdue_reservation(order, product)

    with patch("notifications.enqueue.async_task") as mock_async:
        expire_overdue_reservations(now=timezone.now())

        # on_commit registered, but not yet fired
        assert mock_async.call_count == 0

        # Fire the on_commit callbacks
        assert len(callbacks) == 1
        callbacks[0]()

        mock_async.assert_called_once()
        args, kwargs = mock_async.call_args
        assert args[0] == "notifications.jobs.send_order_system_cancelled_notification"
        assert kwargs["recipient_email"] == "customer@example.com"
        assert kwargs["order_id"] == order.id


def test_notification_enqueued_for_each_cancelled_order(monkeypatch):
    """One on_commit callback is registered per cancelled order."""
    callbacks = _capture_on_commit(monkeypatch)

    product_a = Product.objects.create(
        name="PROD_NOTIF_B1", price="10.00", stock_quantity=5, is_active=True
    )
    product_b = Product.objects.create(
        name="PROD_NOTIF_B2", price="10.00", stock_quantity=5, is_active=True
    )
    order_a = _make_order("a@example.com")
    order_b = _make_order("b@example.com")
    _create_overdue_reservation(order_a, product_a)
    _create_overdue_reservation(order_b, product_b)

    with patch("notifications.enqueue.async_task"):
        expire_overdue_reservations(now=timezone.now())

    # One on_commit per cancelled order
    assert len(callbacks) == 2


# ---------------------------------------------------------------------------
# B) No overdue reservations → no notification enqueued
# ---------------------------------------------------------------------------


def test_no_notification_when_no_overdue_reservations(monkeypatch):
    """When there are no overdue reservations, no on_commit callback and no
    notification job is enqueued."""
    callbacks = _capture_on_commit(monkeypatch)

    product = Product.objects.create(
        name="PROD_NOTIF_C", price="10.00", stock_quantity=5, is_active=True
    )
    order = _make_order("other@example.com")
    # Reservation expires in the future — should NOT be expired
    InventoryReservation.objects.create(
        order=order,
        product=product,
        quantity=1,
        status=InventoryReservation.Status.ACTIVE,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    with patch("notifications.enqueue.async_task") as mock_async:
        expire_overdue_reservations(now=timezone.now())

    assert len(callbacks) == 0
    mock_async.assert_not_called()


def test_no_notification_for_already_paid_order(monkeypatch):
    """Overdue reservations belonging to a PAID order are skipped; no
    notification is enqueued."""
    callbacks = _capture_on_commit(monkeypatch)

    product = Product.objects.create(
        name="PROD_NOTIF_D", price="10.00", stock_quantity=5, is_active=True
    )
    # PAID order — service skips it
    order = _make_order("paid@example.com", status=Order.Status.PAID)
    _create_overdue_reservation(order, product)

    with patch("notifications.enqueue.async_task") as mock_async:
        expire_overdue_reservations(now=timezone.now())

    assert len(callbacks) == 0
    mock_async.assert_not_called()


# ---------------------------------------------------------------------------
# C) Enqueue failure does not break expiration flow
# ---------------------------------------------------------------------------


def test_enqueue_failure_does_not_break_expiration(monkeypatch):
    """If enqueue_best_effort raises internally, the expiration result is still
    returned and the order is still cancelled in the DB."""
    callbacks = _capture_on_commit(monkeypatch)

    product = Product.objects.create(
        name="PROD_NOTIF_E", price="10.00", stock_quantity=5, is_active=True
    )
    order = _make_order("fail@example.com")
    _create_overdue_reservation(order, product)

    # async_task raises — enqueue_best_effort swallows it internally
    with patch("notifications.enqueue.async_task", side_effect=Exception("broker down")):
        affected = expire_overdue_reservations(now=timezone.now())

        assert len(callbacks) == 1
        # Executing the callback must not raise
        callbacks[0]()   # enqueue_best_effort swallows the exception

    # Expiration result is unaffected
    assert affected == 1

    # Order is cancelled in the DB
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED


# ---------------------------------------------------------------------------
# D) Renderer
# ---------------------------------------------------------------------------


def test_renderer_includes_order_id():
    """render_order_system_cancelled_notification includes the order ID in both
    subject and body."""
    subject, body = render_order_system_cancelled_notification(
        recipient_email="r@example.com", order_id=42
    )
    assert "42" in subject
    assert "42" in body


def test_renderer_includes_recipient_email():
    """render_order_system_cancelled_notification includes the email address in
    the greeting."""
    _, body = render_order_system_cancelled_notification(
        recipient_email="hello@example.com", order_id=1
    )
    assert "hello@example.com" in body


def test_renderer_mentions_cancellation():
    """Body communicates that the order was cancelled."""
    _, body = render_order_system_cancelled_notification(
        recipient_email="r@example.com", order_id=7
    )
    assert "cancelled" in body.lower()
