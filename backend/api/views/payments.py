from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from payments.models import Payment


class PaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order = get_object_or_404(
            Order,
            id=request.data["order_id"],
            user=request.user,
            status=Order.Status.CREATED,
        )

        if hasattr(order, "payment"):
            raise ValidationError("Payment already exists.")

        result = request.data.get("result")

        status_map = {
            "success": Payment.Status.SUCCESS,
            "fail": Payment.Status.FAILED,
        }

        if result not in status_map:
            raise ValidationError("Invalid payment result.")

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
