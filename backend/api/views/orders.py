from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from api.serializers.order import OrderSerializer


class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
