from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from carts.models import Cart, CartItem
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

        item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            price_at_add_time=product.price,
        )

        return Response(
            {
                "id": item.id,
                "quantity": item.quantity,
                "price_at_add_time": str(item.price_at_add_time),
            },
            status=status.HTTP_201_CREATED,
        )
