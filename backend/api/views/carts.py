from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from api.serializers.order import OrderSerializer
from carts.models import Cart, CartItem
from orders.models import Order
from orderitems.models import OrderItem
from products.models import Product
from api.serializers.cart import CartSerializer


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            status=Cart.Status.ACTIVE,
        )
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            status=Cart.Status.ACTIVE,
        )

        product = Product.objects.get(id=request.data["product_id"])
        quantity = int(request.data["quantity"])

        try:
            item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                price_at_add_time=product.price,
            )
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict or e.messages)

        return Response(
            {
                "id": item.id,
                "quantity": item.quantity,
                "price_at_add_time": str(item.price_at_add_time),
            },
            status=status.HTTP_201_CREATED,
        )


class CartCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.get(
                user=request.user,
                status=Cart.Status.ACTIVE,
            )
        except Cart.DoesNotExist:
            raise DRFValidationError("No active cart to checkout.")

        if not cart.items.exists():
            raise DRFValidationError("Cart is empty.")

        order = Order.objects.create(
            user=request.user,
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_at_order_time=item.price_at_add_time,
            )

        cart.status = Cart.Status.CONVERTED
        cart.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=201)
