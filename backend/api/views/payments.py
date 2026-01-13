from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample
from api.serializers.payment import PaymentCreateRequestSerializer
from api.serializers.payment_response import PaymentResponseSerializer
from api.serializers.common import ErrorResponseSerializer
from api.exceptions.base import NotFoundException
from api.exceptions.payment import (
    PaymentAlreadyExistsException,
    OrderNotPayableException
)
from orders.models import Order, InventoryReservation
from payments.models import Payment
from orders.services.inventory_reservation_service import (
    commit_reservations_for_paid,
    release_reservations,
)


class PaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Create payment for an order",
        description="""
Simulates a payment gateway interaction.

This endpoint creates a payment for an order and immediately updates
the order status based on the simulated payment result.

Behavior:
- Only orders in CREATED status can be paid.
- Each order can have only one payment.
- Payment result is simulated via request payload.

Side effects:
- On success: Order status is set to PAID.
- On failure: Order status is set to PAYMENT_FAILED.

Notes:
- This is a fake payment gateway used for development and testing.
- Payments are synchronous and non-retryable.
""",
        request=PaymentCreateRequestSerializer,
        responses={
            201: PaymentResponseSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Successful payment",
                value={
                    "order_id": 123,
                    "result": "success"
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Payment success response",
                value={
                    "id": 10,
                    "status": "SUCCESS",
                    "order": 123
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                name="Order not found or not payable",
                value={
                    "code": "NOT_FOUND",
                    "message": "Order not found."
                },
                response_only=True,
                status_codes=["404"],
            ),
            OpenApiExample(
                name="Payment already exists",
                value={
                    "code": "PAYMENT_ALREADY_EXISTS",
                    "message": "Payment already exists."
                },
                response_only=True,
                status_codes=["409"],
            ),
            OpenApiExample(
                name="Order not payable",
                value={
                    "code": "ORDER_NOT_PAYABLE",
                    "message": "Order is not payable in its current state.",
                },
                response_only=True,
                status_codes=["409"],
            ),
            OpenApiExample(
                name="Invalid payment result",
                value={
                    "code": "VALIDATION_ERROR",
                    "message": "One or more fields have errors.",
                    "errors": {"result": ['"maybe" is not a valid choice.']},
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        serializer = PaymentCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data["order_id"]
        payment_result = serializer.validated_data["result"]

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            raise NotFoundException("Order not found.")

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
            status=status_map[payment_result],
        )

        if payment.status == Payment.Status.SUCCESS:
            commit_reservations_for_paid(order=order)
        else:
            release_reservations(
                order=order,
                reason=InventoryReservation.ReleaseReason.PAYMENT_FAILED,
                cancelled_by=Order.CancelledBy.SYSTEM,
                cancel_reason=Order.CancelReason.PAYMENT_FAILED,
            )

        return Response(PaymentResponseSerializer(payment).data, status=201)
