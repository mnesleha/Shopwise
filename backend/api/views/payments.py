from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample
from api.serializers.payment import PaymentCreateRequestSerializer
from api.serializers.common import ErrorResponseSerializer
from api.exceptions.payment import (
    PaymentAlreadyExistsException,
    InvalidPaymentResultException,
    OrderNotPayableException
)
from orders.models import Order
from payments.models import Payment


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
            201: None,  # response is inline dict, documented via examples
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
                    "code": "not_found",
                    "message": "Order not found or not payable."
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
                    "detail": "Order is not payable in its current state.",
                    "code": "ORDER_NOT_PAYABLE",
                },
                response_only=True,
                status_codes=["409"],
            ),
            OpenApiExample(
                name="Invalid payment result",
                value={
                    "code": "INVALID_PAYMENT_RESULT",
                    "message": "Invalid payment result."
                },
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        order = get_object_or_404(
            Order,
            id=request.data["order_id"],
            user=request.user,
        )

        if order.status != Order.Status.CREATED:
            raise OrderNotPayableException()

        if hasattr(order, "payment"):
            raise PaymentAlreadyExistsException()

        result = request.data.get("result")

        status_map = {
            "success": Payment.Status.SUCCESS,
            "fail": Payment.Status.FAILED,
        }

        if result not in status_map:
            raise InvalidPaymentResultException()

        payment = Payment.objects.create(
            order=order,
            status=status_map[result],
        )

        order.status = (
            Order.Status.PAID
            if payment.status == Payment.Status.SUCCESS
            else Order.Status.PAYMENT_FAILED
        )
        order.save()

        return Response(
            {
                "id": payment.id,
                "status": payment.status,
                "order": order.id,
            },
            status=201,
        )
