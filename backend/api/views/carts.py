import secrets

from django.conf import settings
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError
from carts.models import Cart, CartItem
from carts.services.resolver import (
    extract_cart_token,
    get_active_anonymous_cart_by_token,
    hash_cart_token,
)
from orders.models import Order
from orderitems.models import OrderItem
from products.models import Product
from api.serializers.cart import (
    CartSerializer,
    CartItemCreateRequestSerializer,
    CartItemSerializer,
    CartItemUpdateRequestSerializer,
    CartCheckoutRequestSerializer,
    CartCheckoutResponseSerializer,
)
from api.serializers.common import ErrorResponseSerializer
from api.services.pricing import calculate_price
from api.services.cookies import cart_token_cookie_kwargs
from carts.services.tokens import generate_cart_token
from api.exceptions import ProductUnavailableException
from api.exceptions.orders import OutOfStockException
from api.exceptions.cart import (
    # Cart checkout exceptions
    NoActiveCartException,
    CartEmptyException,
    CheckoutFailedException,
    # Cart item exceptions
    CartItemInvalidQuantityException,
    CartItemMissingFieldException,
    CartItemQuantityNotIntegerException,
    ProductNotFoundException,
)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiParameter,
)
from orders.services.inventory_reservation_service import reserve_for_checkout

CART_TOKEN_PARAMETERS = [
    OpenApiParameter(
        name="X-Cart-Token",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.HEADER,
        required=False,
        description="Optional anonymous cart token.",
    ),
    OpenApiParameter(
        name="cart_token",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.COOKIE,
        required=False,
        description="Optional anonymous cart token cookie.",
    ),
]


def _resolve_or_create_cart(request):
    """
    Resolve or create a cart for the given request.

    Behavior:
    - Authenticated users: return (or lazily create) the user's ACTIVE cart.
    - Anonymous users: resolve an ACTIVE anonymous cart via token (header/cookie),
      or create a new anonymous ACTIVE cart when missing/invalid.

    Returns:
        A tuple (cart, created, raw_token_or_none) where raw_token_or_none is the newly generated
        guest token when a new anonymous cart was created (used to set the cookie).
    """

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            status=Cart.Status.ACTIVE,
        )
        return cart, created, None

    raw_token = extract_cart_token(request)
    if raw_token:
        cart = get_active_anonymous_cart_by_token(raw_token)
        if cart:
            return cart, False, None

    cart, raw_token = _create_anonymous_cart_with_unique_token()
    return cart, True, raw_token


def _get_active_cart_for_request(request):
    """
    Return the current ACTIVE cart for the request context.

    - If authenticated: resolves/creates the user's ACTIVE cart.
    - If anonymous: resolves an ACTIVE anonymous cart by token; may return None
      if no valid token is present (depending on implementation).
    """

    if request.user.is_authenticated:
        return Cart.objects.filter(
            user=request.user,
            status=Cart.Status.ACTIVE,
        ).first()

    raw_token = extract_cart_token(request)
    if not raw_token:
        return None

    return get_active_anonymous_cart_by_token(raw_token)


def _create_anonymous_cart_with_unique_token(max_attempts: int = 3):
    """
    Create an anonymous ACTIVE cart with a freshly generated token hash.

    Retries on DB unique constraint collision for anonymous_token_hash.
    This is a deterministic stand-in for rare token collisions / race conditions.

    Returns:
        (cart, raw_token)

    Raises:
        IntegrityError: if collisions persist beyond max_attempts.
    """
    last_error = None
    for _ in range(max_attempts):
        raw_token = generate_cart_token()
        token_hash = hash_cart_token(raw_token)
        try:
            cart = Cart.objects.create(
                user=None,
                status=Cart.Status.ACTIVE,
                anonymous_token_hash=token_hash,
            )
            return cart, raw_token
        except IntegrityError as e:
            last_error = e
            continue
        except DjangoValidationError as e:
            # With Cart.save() calling full_clean(), uniqueness collisions may surface
            # as ValidationError before hitting the DB layer.
            msg_dict = getattr(e, "message_dict", None) or {}
            if "anonymous_token_hash" in msg_dict:
                last_error = e
                continue
            raise
    # If we still fail, bubble up (global handler should turn into {code,message} not 500).
    raise last_error


class CartView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Cart"],
        summary="Retrieve active cart",
        description="""
Returns the user's active cart.

Behavior:
- If an ACTIVE cart exists, it is returned.
- If no ACTIVE cart exists, a new cart is created automatically.
- If the request is anonymous and a new cart is created, a `cart_token`
  cookie is set on the response.

Important notes:
- This endpoint has a side-effect (cart creation).
- The operation is not strictly read-only.
- This behavior is intentional to simplify frontend integration.

HTTP semantics:
- 200 OK: an existing active cart is returned
- 201 Created: a new active cart was created (target behavior)
""",
        parameters=CART_TOKEN_PARAMETERS,
        responses={
            200: CartSerializer,
            201: CartSerializer,
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
        ],
    )
    def get(self, request):
        cart, created, raw_token = _resolve_or_create_cart(request)
        serializer = CartSerializer(cart)
        response = Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
        if raw_token:
            response.set_cookie(
                "cart_token",
                raw_token,
                **cart_token_cookie_kwargs(),
            )
        return response


class CartItemCreateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Cart Items"],
        summary="Add item to active cart",
        description="""
Adds a product to the user's active cart.

Business rules:
- If no active cart exists, a new one is created automatically.
- Quantity must be greater than zero.
- Product price is snapshotted at add time.

Pricing behavior
- Product price is snapshotted at add time (`price_at_add_time`)
- Discounts are NOT applied at this stage

Error handling strategy:
- 400 Bad Request: request is malformed or fails validation (e.g. invalid quantity)
- 404 Not Found: referenced product does not exist
- 409 Conflict: product exists but cannot be added to the cart
  (e.g. out of stock, inactive, business rule violation)

Notes:
- Error handling behavior reflects the target API contract.
- Not all scenarios may be fully implemented yet.
- Anonymous requests may receive a `cart_token` cookie when a new cart
  is created.
""",
        request=CartItemCreateRequestSerializer,
        parameters=CART_TOKEN_PARAMETERS,
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
        data = request.data

        # --- required fields ---
        if "product_id" not in data or "quantity" not in data:
            raise CartItemMissingFieldException()

        # --- quantity parsing ---
        try:
            quantity = int(data["quantity"])
        except (TypeError, ValueError):
            raise CartItemQuantityNotIntegerException()

        if quantity <= 0:
            raise CartItemInvalidQuantityException()

        # --- cart ---
        cart, _, raw_token = _resolve_or_create_cart(request)

        # --- product ---
        try:
            product = Product.objects.get(id=data["product_id"])
        except Product.DoesNotExist:
            raise ProductNotFoundException()

        if not product.is_sellable():
            raise ProductUnavailableException()

        if quantity > product.stock_quantity:
            raise OutOfStockException()

        # --- create item ---
        item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            price_at_add_time=product.price,
        )

        response = Response(
            CartItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )
        if raw_token:
            response.set_cookie(
                "cart_token",
                raw_token,
                **cart_token_cookie_kwargs(),
            )
        return response


class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Cart Items"],
        summary="Set cart item quantity",
        request=CartItemUpdateRequestSerializer,
        parameters=CART_TOKEN_PARAMETERS,
        responses={
            200: CartSerializer,
            201: CartSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
    )
    def put(self, request, product_id: int):
        serializer = CartItemUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]

        cart, _, raw_token = _resolve_or_create_cart(request)

        if quantity == 0:
            CartItem.objects.filter(cart=cart, product_id=product_id).delete()
            response = Response(CartSerializer(cart).data, status=200)
            if raw_token:
                response.set_cookie(
                    "cart_token",
                    raw_token,
                    **cart_token_cookie_kwargs(),
                )
            return response

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ProductNotFoundException()

        if not product.is_sellable():
            raise ProductUnavailableException()

        if quantity > product.stock_quantity:
            raise OutOfStockException()

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity, "price_at_add_time": product.price},
        )
        if not created:
            item.quantity = quantity
            item.save(update_fields=["quantity"])

        response = Response(
            CartSerializer(cart).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
        if raw_token:
            response.set_cookie(
                "cart_token",
                raw_token,
                **cart_token_cookie_kwargs(),
            )
        return response

    @extend_schema(
        tags=["Cart Items"],
        summary="Remove cart item",
        parameters=CART_TOKEN_PARAMETERS,
        responses={
            200: CartSerializer,
        },
    )
    def delete(self, request, product_id: int):
        cart, _, raw_token = _resolve_or_create_cart(request)
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()

        response = Response(CartSerializer(cart).data, status=200)
        if raw_token:
            response.set_cookie(
                "cart_token",
                raw_token,
                **cart_token_cookie_kwargs(),
            )
        return response


class CartCheckoutView(APIView):
    permission_classes = [AllowAny]

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

Pricing behavior
- Final prices are calculated at checkout
- Pricing rules:
  - FIXED discount has priority over PERCENT
  - Only one discount per product
  - Final price is never negative
  - Rounding: ROUND_HALF_UP (2 decimal places)

Price consistency
- Uses `price_at_add_time`
- Product price changes after adding to cart do not affect checkout

Error handling strategy:
- 400 Bad Request: cart exists but is empty
- 404 Not Found: no ACTIVE cart exists
- 409 Conflict: cart cannot be checked out due to state conflict
  (e.g. already converted, concurrent checkout)

Notes:
- Error handling reflects the target API contract.
- Some conflict scenarios may not be fully implemented yet.
""",
        request=CartCheckoutRequestSerializer,
        parameters=CART_TOKEN_PARAMETERS,
        responses={
            201: CartCheckoutResponseSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                name="Checkout successful",
                value={
                    "id": 123,
                    "status": "CREATED",
                    "items": [
                        {
                            "id": 1,
                            "product": 42,
                            "quantity": 2,
                            "unit_price": "25.00",
                            "line_total": "40.00",
                            "discount": {
                                "type": "PERCENT",
                                "value": "20.00"
                            }
                        }
                    ],
                    "total": "40.00"
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                name="Cart is empty",
                value={
                    "code": "CART_EMPTY",
                    "message": "Cart is empty."
                },
                status_codes=["400"],
            ),
            OpenApiExample(
                name="No active cart",
                value={
                    "code": "NO_ACTIVE_CART",
                    "message": "No active cart to checkout."
                },
                status_codes=["404"],
            ),
        ],
    )
    def post(self, request):
        serializer = CartCheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        checkout_data = serializer.validated_data

        try:
            with transaction.atomic():
                try:
                    cart = _get_active_cart_for_request(request)
                    if not cart:
                        raise Cart.DoesNotExist()
                    cart = (
                        Cart.objects
                        .select_for_update()
                        .get(pk=cart.pk)
                    )
                except Cart.DoesNotExist:
                    raise NoActiveCartException()

                if not cart.items.exists():
                    raise CartEmptyException()

                order = Order(
                    user=request.user if request.user.is_authenticated else None,
                    customer_email=checkout_data["customer_email"],
                    shipping_name=checkout_data["shipping_name"],
                    shipping_address_line1=checkout_data["shipping_address_line1"],
                    shipping_address_line2=checkout_data.get(
                        "shipping_address_line2", ""
                    ),
                    shipping_city=checkout_data["shipping_city"],
                    shipping_postal_code=checkout_data["shipping_postal_code"],
                    shipping_country=checkout_data["shipping_country"],
                    shipping_phone=checkout_data["shipping_phone"],
                    billing_same_as_shipping=checkout_data.get(
                        "billing_same_as_shipping", True
                    ),
                    billing_name=checkout_data.get("billing_name"),
                    billing_address_line1=checkout_data.get("billing_address_line1"),
                    billing_address_line2=checkout_data.get("billing_address_line2"),
                    billing_city=checkout_data.get("billing_city"),
                    billing_postal_code=checkout_data.get("billing_postal_code"),
                    billing_country=checkout_data.get("billing_country"),
                    billing_phone=checkout_data.get("billing_phone"),
                )
                try:
                    order.full_clean()
                except DjangoValidationError as exc:
                    raise DRFValidationError(exc.message_dict)
                order.save()

                reservation_items = [
                    {"product_id": item.product_id, "quantity": item.quantity}
                    for item in cart.items.all()
                ]

                for item in cart.items.all():
                    pricing = calculate_price(
                        unit_price=item.price_at_add_time,
                        quantity=item.quantity,
                        discounts=item.product.discounts.all(),
                    )

                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price_at_order_time=pricing.final_price,
                        unit_price_at_order_time=item.price_at_add_time,
                        line_total_at_order_time=pricing.final_price,
                        applied_discount_type_at_order_time=(
                            pricing.applied_discount.discount_type
                            if pricing.applied_discount
                            else None
                        ),
                        applied_discount_value_at_order_time=(
                            pricing.applied_discount.value
                            if pricing.applied_discount
                            else None
                        ),
                    )

                reserve_for_checkout(order=order, items=reservation_items)

                cart.status = Cart.Status.CONVERTED
                cart.save()

        except APIException:
            raise

        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict)

        except Exception:
            # atomic block guarantees rollback
            raise CheckoutFailedException()

        return Response(
            CartCheckoutResponseSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )
