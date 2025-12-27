from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
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
from api.serializers.cart import CartSerializer, CartItemCreateRequestSerializer, CartItemSerializer, CartCheckoutResponseSerializer
from api.serializers.common import ErrorResponseSerializer
from api.exceptions import ProductUnavailableException
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiExample


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Cart"],
        summary="Retrieve active cart",
        description="""
Returns the user's active cart.

Behavior:
- If an ACTIVE cart exists, it is returned.
- If no ACTIVE cart exists, a new cart is created automatically.

Important notes:
- This endpoint has a side-effect (cart creation).
- The operation is not strictly read-only.
- This behavior is intentional to simplify frontend integration.

HTTP semantics:
- 200 OK: an existing active cart is returned
- 201 Created: a new active cart was created (target behavior)
- 403 Forbidden: user is not authenticated
""",
        responses={
            200: CartSerializer,
            201: CartSerializer,
            403: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Existing active cart",
                value={
                    "id": 10,
                    "status": "ACTIVE",
                    "items": [
                        {
                            "id": 5,
                            "product": 42,
                            "quantity": 2,
                            "price_at_add_time": "19.99"
                        }
                    ]
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                name="Newly created empty cart",
                value={
                    "id": 11,
                    "status": "ACTIVE",
                    "items": []
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                name="Unauthorized user attempt",
                value={
                    "detail": "Authentication credentials were not provided.",
                },
                response_only=True,
                status_codes=["403"],
            ),
        ],
    )
    def get(self, request):
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            status=Cart.Status.ACTIVE,
        )
        serializer = CartSerializer(cart)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Cart Items"],
        summary="Add item to active cart",
        description="""
Adds a product to the user's active cart.

Business rules:
- If no active cart exists, a new one is created automatically.
- Quantity must be greater than zero.
- Product price is snapshotted at add time.

Error handling strategy:
- 400 Bad Request: request is malformed or fails validation (e.g. invalid quantity)
- 404 Not Found: referenced product does not exist
- 409 Conflict: product exists but cannot be added to the cart
  (e.g. out of stock, inactive, business rule violation)

Notes:
- Error handling behavior reflects the target API contract.
- Not all scenarios may be fully implemented yet.
""",
        request=CartItemCreateRequestSerializer,
        responses={
            201: CartItemSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Add 2 items of product 42",
                value={
                    "product_id": 42,
                    "quantity": 2,
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Item successfully added",
                value={
                    "id": 15,
                    "product": 42,
                    "quantity": 2,
                    "price_at_add_time": "19.99",
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                name="Invalid quantity",
                value={
                    "detail": "Quantity must be greater than zero."
                },
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                name="Product not found",
                value={
                    "detail": "Referenced product does not exist."
                },
                response_only=True,
                status_codes=["404"],
            ),
            OpenApiExample(
                name="Product unavailable",
                value={
                    "detail": "Product is currently unavailable."
                },
                response_only=True,
                status_codes=["409"],
            ),
        ],
    )
    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity")

        if product_id is None or quantity is None:
            raise DRFValidationError(
                {"detail": "product_id and quantity are required"})

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise DRFValidationError({"detail": "quantity must be an integer"})

        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            status=Cart.Status.ACTIVE,
        )

        product = get_object_or_404(Product, id=product_id)

        if not product.is_sellable():
            raise ProductUnavailableException()

        try:
            item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity,
                price_at_add_time=product.price,
            )
        except DjangoValidationError as e:
            raise DRFValidationError({"detail": e.messages[0]})

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

    @extend_schema(
        tags=["Cart Checkout"],
        summary="Checkout active cart",
        description="""
Converts the user's active cart into an order.

Workflow:
1. Validates that an ACTIVE cart exists
2. Validates that the cart is not empty
3. Creates an Order and associated OrderItems
4. Marks the cart as CONVERTED

Business rules:
- A cart can be checked out only once
- Orders are immutable
- After checkout, a new ACTIVE cart will be created on next cart retrieval

Error handling strategy:
- 400 Bad Request: cart exists but is empty
- 404 Not Found: no ACTIVE cart exists
- 409 Conflict: cart cannot be checked out due to state conflict
  (e.g. already converted, concurrent checkout)

Notes:
- Error handling reflects the target API contract.
- Some conflict scenarios may not be fully implemented yet.
""",
        responses={
            201: OrderSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Checkout successful",
                value={
                    "id": 123,
                    "status": "CREATED",
                    "items": [
                        {
                            "product": 42,
                            "quantity": 2,
                            "price_at_order_time": "19.99"
                        }
                    ],
                    "total_price": "39.98"
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                name="Cart is empty",
                value={
                    "detail": "Cart is empty."
                },
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                name="No active cart",
                value={
                    "detail": "No active cart to checkout."
                },
                response_only=True,
                status_codes=["404"],
            ),
            OpenApiExample(
                name="Cart already checked out",
                value={
                    "detail": "Cart has already been checked out."
                },
                response_only=True,
                status_codes=["409"],
            ),
        ],
    )
    def post(self, request):
        try:
            cart = Cart.objects.get(
                user=request.user,
                status=Cart.Status.ACTIVE,
            )
        except Cart.DoesNotExist:
            raise DRFValidationError({"detail": "No active cart to checkout."})

        if not cart.items.exists():
            raise DRFValidationError({"detail": "Cart is empty."})

        with transaction.atomic():
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

        response_data = {
            "order": OrderSerializer(order).data
        }

        serializer = CartCheckoutResponseSerializer(
            instance={"order": order}
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )
