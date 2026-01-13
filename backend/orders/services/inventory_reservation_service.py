from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from api.exceptions.orders import OutOfStockException
from orders.models import InventoryReservation, Order
from products.models import Product


def reserve_for_checkout(*, order, items, ttl_minutes=None) -> None:
    if not items:
        return

    now = timezone.now()
    if ttl_minutes is None:
        guest_seconds = getattr(settings, "RESERVATION_TTL_GUEST_SECONDS", 900)
        auth_seconds = getattr(settings, "RESERVATION_TTL_AUTH_SECONDS", 7200)
        ttl_seconds = guest_seconds if order.user_id is None else auth_seconds
        expires_at = now + timedelta(seconds=ttl_seconds)
    else:
        expires_at = now + timedelta(minutes=ttl_minutes)

    requested = {}
    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        requested[product_id] = requested.get(product_id, 0) + quantity

    product_ids = sorted(requested.keys())

    with transaction.atomic():
        products = (
            Product.objects.select_for_update()
            .filter(id__in=product_ids)
            .order_by("id")
        )
        product_map = {product.id: product for product in products}

        active_reservations = (
            InventoryReservation.objects.select_for_update()
            .filter(
                product_id__in=product_ids,
                status=InventoryReservation.Status.ACTIVE,
                expires_at__gt=now,
            )
            .order_by("product_id")
        )
        reserved_totals = {}
        for reservation in active_reservations:
            reserved_totals[reservation.product_id] = (
                reserved_totals.get(reservation.product_id, 0)
                + reservation.quantity
            )

        for product_id in product_ids:
            product = product_map.get(product_id)
            if product is None:
                raise OutOfStockException()
            available = product.stock_quantity - reserved_totals.get(product_id, 0)
            if requested[product_id] > available:
                raise OutOfStockException()

        reservations = [
            InventoryReservation(
                order=order,
                product_id=product_id,
                quantity=requested[product_id],
                status=InventoryReservation.Status.ACTIVE,
                expires_at=expires_at,
            )
            for product_id in product_ids
        ]
        InventoryReservation.objects.bulk_create(reservations)


def commit_reservations_for_paid(*, order) -> None:
    """
    Commit ACTIVE reservations for a paid order, decrementing physical stock.
    Idempotent: if all reservations are already COMMITTED, this is a no-op.
    """
    with transaction.atomic():
        reservations = (
            InventoryReservation.objects.select_for_update()
            .filter(order=order)
            .order_by("product_id")
        )
        if not reservations.exists():
            return

        if not reservations.exclude(status=InventoryReservation.Status.COMMITTED).exists():
            return

        if reservations.filter(status=InventoryReservation.Status.ACTIVE).count() == 0:
            return

        active_reservations = list(
            reservations.filter(status=InventoryReservation.Status.ACTIVE)
        )
        order_quantities = {}
        for reservation in active_reservations:
            order_quantities[reservation.product_id] = (
                order_quantities.get(reservation.product_id, 0)
                + reservation.quantity
            )

        product_ids = sorted(order_quantities.keys())
        products = (
            Product.objects.select_for_update()
            .filter(id__in=product_ids)
            .order_by("id")
        )
        product_map = {product.id: product for product in products}

        active_reservations_all = (
            InventoryReservation.objects.select_for_update()
            .filter(
                product_id__in=product_ids,
                status=InventoryReservation.Status.ACTIVE,
            )
            .order_by("product_id")
        )
        active_sum_map = {}
        for reservation in active_reservations_all:
            active_sum_map[reservation.product_id] = (
                active_sum_map.get(reservation.product_id, 0)
                + reservation.quantity
            )

        now = timezone.now()
        for product_id in product_ids:
            product = product_map.get(product_id)
            if product is None:
                _cancel_order_out_of_stock(order, active_reservations, now)
                raise OutOfStockException()
            active_sum = active_sum_map.get(product_id, 0) or 0
            available = product.stock_quantity - active_sum
            if available < 0 or product.stock_quantity < order_quantities[product_id]:
                _cancel_order_out_of_stock(order, active_reservations, now)
                raise OutOfStockException()

        for product_id in product_ids:
            product = product_map[product_id]
            product.stock_quantity -= order_quantities[product_id]
            product.save(update_fields=["stock_quantity"])

        for reservation in active_reservations:
            reservation.status = InventoryReservation.Status.COMMITTED
            reservation.committed_at = now
        InventoryReservation.objects.bulk_update(
            active_reservations,
            ["status", "committed_at"],
        )

        if order.status == _order_status_created_value():
            order.status = _order_status_paid_value()
            order.save(update_fields=["status"])


def release_reservations(*, order, reason, cancelled_by, cancel_reason) -> None:
    """
    Release ACTIVE reservations for an order. Idempotent when no ACTIVE rows exist.
    """
    with transaction.atomic():
        active_reservations = list(
            InventoryReservation.objects.select_for_update()
            .filter(order=order, status=InventoryReservation.Status.ACTIVE)
            .order_by("product_id")
        )
        now = timezone.now()

        if active_reservations:
            for reservation in active_reservations:
                reservation.status = InventoryReservation.Status.RELEASED
                reservation.released_at = now
                reservation.release_reason = reason
            InventoryReservation.objects.bulk_update(
                active_reservations,
                ["status", "released_at", "release_reason"],
            )

        if order.status == _order_status_created_value():
            order.status = _order_status_cancelled_value()
            order.cancel_reason = cancel_reason
            order.cancelled_by = cancelled_by
            order.cancelled_at = now
            order.save(
                update_fields=[
                    "status",
                    "cancel_reason",
                    "cancelled_by",
                    "cancelled_at",
                ]
            )


def expire_overdue_reservations(*, now=None) -> int:
    """
    Expire ACTIVE reservations past their TTL for orders in CREATED state.
    Returns the number of reservations transitioned to EXPIRED/RELEASED.
    """
    current_time = now or timezone.now()
    affected = 0

    with transaction.atomic():
        order_ids = (
            InventoryReservation.objects.filter(
                status=InventoryReservation.Status.ACTIVE,
                expires_at__lt=current_time,
            )
            .values_list("order_id", flat=True)
            .distinct()
        )

        for order_id in sorted(order_ids):
            order_locked = (
                Order.objects.select_for_update()
                .filter(id=order_id)
                .first()
            )
            if not order_locked:
                continue

            if order_locked.status != _order_status_created_value():
                continue

            overdue_reservations = list(
                InventoryReservation.objects.select_for_update()
                .filter(
                    order_id=order_id,
                    status=InventoryReservation.Status.ACTIVE,
                    expires_at__lt=current_time,
                )
                .order_by("product_id")
            )

            if not overdue_reservations:
                continue

            for reservation in overdue_reservations:
                reservation.status = InventoryReservation.Status.EXPIRED
            InventoryReservation.objects.bulk_update(
                overdue_reservations,
                ["status"],
            )
            affected += len(overdue_reservations)

            order_locked.status = _order_status_cancelled_value()
            order_locked.cancel_reason = _order_cancel_reason_value(
                "PAYMENT_EXPIRED"
            )
            order_locked.cancelled_by = _order_cancelled_by_value("SYSTEM")
            order_locked.cancelled_at = current_time
            order_locked.save(
                update_fields=[
                    "status",
                    "cancel_reason",
                    "cancelled_by",
                    "cancelled_at",
                ]
            )

    return affected


def _order_status_created_value():
    return getattr(Order.Status, "CREATED", "CREATED")


def _order_status_paid_value():
    return getattr(Order.Status, "PAID", "PAID")


def _order_status_cancelled_value():
    return getattr(Order.Status, "CANCELLED", getattr(Order.Status, "CANCELED", "CANCELED"))


def _order_cancel_reason_value(value: str):
    reason_enum = getattr(Order, "CancelReason", None)
    if reason_enum and hasattr(reason_enum, value):
        return getattr(reason_enum, value)
    return value


def _order_cancelled_by_value(value: str):
    by_enum = getattr(Order, "CancelledBy", None)
    if by_enum and hasattr(by_enum, value):
        return getattr(by_enum, value)
    return value


def _cancel_order_out_of_stock(order, active_reservations, now):
    for reservation in active_reservations:
        reservation.status = InventoryReservation.Status.RELEASED
        reservation.released_at = now
        reservation.release_reason = InventoryReservation.ReleaseReason.OUT_OF_STOCK
    InventoryReservation.objects.bulk_update(
        active_reservations,
        ["status", "released_at", "release_reason"],
    )

    order.status = _order_status_cancelled_value()
    order.cancel_reason = _order_cancel_reason_value("OUT_OF_STOCK")
    order.cancelled_by = _order_cancelled_by_value("SYSTEM")
    order.cancelled_at = now
    order.save(
        update_fields=[
            "status",
            "cancel_reason",
            "cancelled_by",
            "cancelled_at",
        ]
    )
