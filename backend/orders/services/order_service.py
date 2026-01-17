from django.db import transaction

from api.exceptions.orders import InvalidOrderStateException
from api.exceptions.payment import PaymentAlreadyExistsException, OrderNotPayableException
from orders.models import Order, InventoryReservation
from orders.services.inventory_reservation_service import (
    commit_reservations_for_paid,
    release_reservations,
)
from payments.models import Payment


class OrderService:
    @staticmethod
    def cancel_by_customer(order: Order, actor_user) -> Order:
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
        with transaction.atomic():
            if Payment.objects.filter(order=order).exists():
                raise PaymentAlreadyExistsException()

            if order.status != Order.Status.CREATED:
                raise OrderNotPayableException()

            status_map = {
                "success": Payment.Status.SUCCESS,
                "fail": Payment.Status.FAILED,
            }
            payment = Payment.objects.create(
                order=order,
                status=status_map[result],
            )

            if payment.status == Payment.Status.SUCCESS:
                commit_reservations_for_paid(order=order)
                # Ensure explicit state transition even if there are no reservations.
                order.refresh_from_db()
                if order.status != Order.Status.PAID:
                    order.status = Order.Status.PAID
                    order.save(update_fields=["status"])
            else:
                release_reservations(
                    order=order,
                    reason=InventoryReservation.ReleaseReason.PAYMENT_FAILED,
                    cancelled_by=Order.CancelledBy.SYSTEM,
                    cancel_reason=Order.CancelReason.PAYMENT_FAILED,
                )
                # release_reservations sets PAYMENT_FAILED for this reason.
                order.refresh_from_db()

            return payment
