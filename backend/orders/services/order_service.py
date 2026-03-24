from django.db import transaction
from django.utils import timezone

from api.exceptions.orders import InvalidOrderStateException
from orders.models import Order, InventoryReservation
from orders.services.inventory_reservation_service import release_reservations
from payments.models import Payment
from payments.services.payment_orchestration import PaymentOrchestrationService
from auditlog.actions import AuditActions
from auditlog.models import AuditEvent
from auditlog.services import AuditService


class OrderService:
    @staticmethod
    def cancel_by_customer(order: Order, actor_user) -> Order:
        """Cancel order by customer.

        Note:
            The ``actor_user`` argument is intentionally kept even though it is not
            used yet. We keep it to make future auditing / authorization refactors
            straightforward without changing the public service signature.
        """
        if order.status != Order.Status.CREATED:
            raise InvalidOrderStateException()

        release_reservations(
            order=order,
            reason=InventoryReservation.ReleaseReason.CUSTOMER_REQUEST,
            cancelled_by=Order.CancelledBy.CUSTOMER,
            cancel_reason=Order.CancelReason.CUSTOMER_REQUEST,
        )
        order.refresh_from_db()
        return order

    @staticmethod
    def create_payment_and_apply_result(
        order: Order, result: str, actor_user
    ) -> Payment:
        """Create a new payment attempt for an order and apply its result.

        Delegates to PaymentOrchestrationService.  The ``result`` string
        ("success" / "fail") is forwarded as DEV_FAKE extra context.

        Note:
            ``actor_user`` is reserved for future auditing/authorization.
        """
        if result not in ("success", "fail"):
            raise ValueError(f"Invalid payment result: {result!r}")

        return PaymentOrchestrationService.start_payment(
            order=order,
            payment_method=None,  # legacy callers don't specify a method
            extra={"simulated_result": result},
        )

    @staticmethod
    def ship_by_admin(order: Order, actor_user) -> Order:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if order.status != Order.Status.PAID:
                raise InvalidOrderStateException()

            status_from = order.status
            order.status = Order.Status.SHIPPED
            order.save(update_fields=["status"])

            AuditService.emit(
                entity_type="order",
                entity_id=str(order.id),
                action=AuditActions.ORDER_SHIPPED,
                actor_type=AuditEvent.ActorType.ADMIN,
                actor_user=actor_user,
                metadata={"status_from": status_from,
                          "status_to": order.status},
                fail_silently=True,
            )
            return order

    @staticmethod
    def deliver_by_admin(order: Order, actor_user) -> Order:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if order.status != Order.Status.SHIPPED:
                raise InvalidOrderStateException()

            status_from = order.status
            order.status = Order.Status.DELIVERED
            order.save(update_fields=["status"])

            AuditService.emit(
                entity_type="order",
                entity_id=str(order.id),
                action=AuditActions.ORDER_DELIVERED,
                actor_type=AuditEvent.ActorType.ADMIN,
                actor_user=actor_user,
                metadata={"status_from": status_from,
                          "status_to": order.status},
                fail_silently=True,
            )
            return order

    @staticmethod
    def cancel_by_admin(order: Order, actor_user) -> Order:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            if order.status not in (
                Order.Status.CREATED,
                Order.Status.PAYMENT_FAILED,
            ):
                raise InvalidOrderStateException()

            status_from = order.status

            now = timezone.now()

            Order.objects.filter(pk=order.pk).update(
                status=Order.Status.CANCELLED,
                cancelled_by=Order.CancelledBy.ADMIN,
                cancel_reason=Order.CancelReason.ADMIN_CANCELLED,
                cancelled_at=now,
            )
            order.refresh_from_db()

            AuditService.emit(
                entity_type="order",
                entity_id=str(order.id),
                action=AuditActions.ORDER_CANCELLED_ADMIN,
                actor_type=AuditEvent.ActorType.ADMIN,
                actor_user=actor_user,
                metadata={"status_from": status_from,
                          "status_to": order.status},
                fail_silently=True,
            )
            return order
