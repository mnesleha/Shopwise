from orders.models import Order
from payments.models import Payment


class ShipmentEligibilityService:
    @staticmethod
    def get_payment_method(*, order) -> str | None:
        return (
            order.payments.order_by("-created_at", "-pk")
            .values_list("payment_method", flat=True)
            .first()
        )

    @classmethod
    def can_create_shipment(cls, *, order) -> bool:
        if order.status == Order.Status.PAID:
            return True

        if order.status != Order.Status.CREATED:
            return False

        return cls.get_payment_method(order=order) == Payment.PaymentMethod.COD