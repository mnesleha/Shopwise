from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from api.serializers.order import OrderResponseSerializer
from orders.services.guest_order_access_service import GuestOrderAccessService


class GuestOrderRetrieveView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, order_id: int):
        token = request.query_params.get("token")
        order = GuestOrderAccessService.validate(
            order_id=order_id,
            token=token,
        )
        if order is None:
            raise Http404()
        return Response(OrderResponseSerializer(order).data, status=200)
