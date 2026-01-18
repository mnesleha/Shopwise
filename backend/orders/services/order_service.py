from django.db import transaction

from api.exceptions.orders import InvalidOrderStateException
from api.exceptions.payment import PaymentAlreadyExistsException, OrderNotPayableException
from orders.models import Order, InventoryReservation
from orders.services.inventory_reservation_service import (
    commit_reservations_for_paid,
    release_reservations
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
            order = (
                Order.objects.select_for_update()
                .filter(id=order.id)
                .first()
            )
            if not order:
                raise OrderNotPayableException()

            status_map = {
                "success": Payment.Status.SUCCESS,
                "fail": Payment.Status.FAILED,
            }

            # If a SUCCESS payment already exists, block any further attempts.
            # This must take precedence over order status checks to return the expected error code.
            if Payment.objects.filter(
                order=order,
                status=Payment.Status.SUCCESS,
            ).exists():
                raise PaymentAlreadyExistsException()

            # Payable states: CREATED (first attempt) or PAYMENT_FAILED (retry).
            if order.status not in (Order.Status.CREATED, Order.Status.PAYMENT_FAILED):
                raise OrderNotPayableException()

            payment = Payment.objects.create(
                order=order,
                status=status_map[result],
            )

            if payment.status == Payment.Status.SUCCESS:
                commit_reservations_for_paid(order=order)
                order.refresh_from_db()
                if order.status != Order.Status.PAID:
                    order.status = Order.Status.PAID
                    order.save(update_fields=["status"])
            else:
                order.status = Order.Status.PAYMENT_FAILED
                order.cancel_reason = Order.CancelReason.PAYMENT_FAILED
                order.save(update_fields=["status", "cancel_reason"])

            return payment
