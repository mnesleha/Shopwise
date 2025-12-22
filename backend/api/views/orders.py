from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from orders.models import Order
from orderitems.models import OrderItem
from products.models import Product
from api.serializers.order import OrderSerializer


class OrderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        order = Order.objects.create(user=request.user)
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="items")
    def add_item(self, request, pk=None):
        order = self.get_object()

        quantity = int(request.data.get("quantity", 0))
        if quantity <= 0:
            raise ValidationError(
                {"quantity": "Quantity must be greater than zero."})

        product = Product.objects.get(id=request.data["product_id"])

        item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price_at_order_time=product.price,
        )

        return Response(
            {
                "id": item.id,
                "quantity": item.quantity,
                "price_at_order_time": str(item.price_at_order_time),
            },
            status=status.HTTP_201_CREATED,
        )
