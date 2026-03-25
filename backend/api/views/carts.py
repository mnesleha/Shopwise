import logging
import secrets
from decimal import Decimal, ROUND_HALF_UP

import sentry_sdk

from django.conf import settings
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError
from carts.models import Cart, CartItem, ActiveCart
from carts.services.resolver import (
    extract_cart_token,
    get_active_anonymous_cart_by_token,
    hash_cart_token,
)
from carts.services.active_cart_service import get_or_create_active_cart_for_user
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
    PaymentInitiationSerializer,
)
from api.serializers.common import ErrorResponseSerializer
from carts.services.pricing import get_cart_pricing, get_cart_pricing_with_order_discount
from carts.services.price_change import detect_price_changes, serialize_price_change_summary
from carts.services.snapshot import get_snapshot_gross_price
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
from orders.services.guest_order_access_service import (
    GuestOrderAccessService,
    generate_guest_access_url,
)
from discounts.models import AcquisitionMode, Offer, OfferStatus
from carts.services.pricing import get_cart_pricing_with_campaign_offer
from api.services.campaign_offer_session import (
    get_claimed_campaign_offer as _get_claimed_campaign_offer,
    set_campaign_offer_cookie as _set_campaign_offer_cookie,
    clear_campaign_offer_cookie as _clear_campaign_offer_cookie,
)
from payments.services.payment_orchestration import PaymentOrchestrationService
from django_q.tasks import async_task
from suppliers.services import resolve_order_supplier_snapshot

from notifications.enqueue import enqueue_best_effort

logger = logging.getLogger(__name__)
from notifications.error_handler import NotificationErrorHandler
from notifications.exceptions import NotificationSendError


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
        try:
            with transaction.atomic():
                cart, created = get_or_create_active_cart_for_user(
                    request.user)
                return cart, created, None
        except IntegrityError:
            # In case of rare pointer races, resolve via ActiveCart row
            ptr = (
                ActiveCart.objects.select_related("cart")
                .filter(user=request.user)
                .first()
            )
            if ptr and ptr.cart and ptr.cart.status == Cart.Status.ACTIVE:
                return ptr.cart, False, None
            cart, created = get_or_create_active_cart_for_user(request.user)
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


class ClaimOfferView(APIView):
    """Claim a campaign offer token into the current session.

    Phase 4 / Slice 5B.

    Validates the offer token and stores it in the session so that
    subsequent cart GET and checkout POST requests apply the campaign
    discount automatically.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Cart"],
        summary="Claim a campaign offer",
        description="""
Validates a campaign offer token and binds it to the current session.

Once claimed, the offer's discount is automatically reflected in
``GET /cart/`` and applied at checkout via the pricing pipeline.

Returns the promotion name and code on success so the frontend can show
a confirmation message.

Error codes:
- ``OFFER_NOT_FOUND`` (404) — token does not exist.
- ``OFFER_INACTIVE`` (400) — offer is inactive or outside its date window.
- ``OFFER_NOT_CLAIMABLE`` (400) — promotion is not ``CAMPAIGN_APPLY``.
""",
        responses={200: None, 400: None, 404: None},
    )
    def post(self, request):
        token = request.data.get("token", "")
        if isinstance(token, str):
            token = token.strip()
        if not token:
            return Response(
                {"code": "OFFER_NOT_FOUND", "message": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            offer = Offer.objects.select_related("promotion").get(token=token)
        except Offer.DoesNotExist:
            return Response(
                {"code": "OFFER_NOT_FOUND", "message": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not offer.is_currently_active():
            return Response(
                {
                    "code": "OFFER_INACTIVE",
                    "message": "This offer is no longer active.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if offer.promotion.acquisition_mode != AcquisitionMode.CAMPAIGN_APPLY:
            return Response(
                {
                    "code": "OFFER_NOT_CLAIMABLE",
                    "message": "This offer cannot be claimed via link.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Persist the token in a dedicated HttpOnly cookie so it is
        # available to the cart GET and checkout endpoints.  A cookie is used
        # (not the Django session) because SESSION_COOKIE_SECURE=True would
        # prevent the browser from storing a session cookie on HTTP in dev.

        # Phase 4 / Offer status: advance lifecycle to CLAIMED.
        # Only move forward (CREATED or DELIVERED → CLAIMED); never downgrade
        # from REDEEMED or EXPIRED.
        Offer.objects.filter(
            pk=offer.pk,
            status__in=[OfferStatus.CREATED, OfferStatus.DELIVERED],
        ).update(status=OfferStatus.CLAIMED)

        # Also persist the token on the current active cart (if one already
        # exists).  This cart-level field acts as the server-side mirror of
        # the cookie and enables best-for-customer comparison during the
        # guest→authenticated cart merge — without it, one side of the
        # comparison would always be invisible to the merge service.
        # Best-effort: a failure here must not abort the claim response.
        try:
            current_cart = _get_active_cart_for_request(request)
            if current_cart is not None:
                current_cart.claimed_offer_token = offer.token
                current_cart.save(update_fields=["claimed_offer_token"])
        except Exception:
            with sentry_sdk.new_scope() as scope:
                scope.set_tag("category", "application")
                scope.set_tag("subsystem", "campaign_offer")
                scope.set_tag("operation", "cart_sync")
                scope.set_context("campaign_offer_cart_sync", {
                    "offer_id": offer.pk,
                    "offer_token_suffix": offer.token[-6:] if offer.token else None,
                    "user_id": getattr(request.user, "pk", None),
                    "is_authenticated": getattr(request.user, "is_authenticated", False),
                })
                logger.warning(
                    "Failed to sync claimed_offer_token to cart (best-effort). offer_id=%s",
                    offer.pk,
                    exc_info=True,
                )

        response = Response(
            {
                "promotion_name": offer.promotion.name,
                "promotion_code": offer.promotion.code,
            },
            status=status.HTTP_200_OK,
        )
        _set_campaign_offer_cookie(response, token)
        return response


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
        serializer = CartSerializer(cart, context={"request": request})
        response = Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        if raw_token:
            response.set_cookie(
                "cart_token",
                raw_token,
                **cart_token_cookie_kwargs(),
            )
        return response

    @extend_schema(
        tags=["Cart"],
        summary="Clear active cart",
        description="""
Removes all items from the active cart without deleting the cart itself.

Behavior:
- Resolves the current active cart for the request context
  (authenticated user cart or anonymous cart by token).
- Deletes all CartItem rows belonging to that cart.
- The Cart row is preserved; the cart remains retrievable as an empty active cart.
- Idempotent: if no active cart exists or the cart is already empty, still returns 204.

HTTP semantics:
- 204 No Content: items cleared (or nothing to clear)
""",
        parameters=CART_TOKEN_PARAMETERS,
        responses={
            204: None,
        },
    )
    def delete(self, request):
        cart = _get_active_cart_for_request(request)
        if cart is not None:
            CartItem.objects.filter(cart=cart).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        # Legacy POST acts as UPSERT (set quantity), aligned with previous behavior.
        created = False
        with transaction.atomic():
            try:
                # INSERT attempt must be in its own savepoint. If it fails on unique constraint,
                # we can still run the fallback SELECT/UPDATE inside this outer transaction.
                with transaction.atomic():
                    item = CartItem.objects.create(
                        cart=cart,
                        product=product,
                        quantity=quantity,
                        price_at_add_time=get_snapshot_gross_price(product),
                    )
                created = True

            except DjangoValidationError as e:
                # CartItem.save() calls full_clean(); uniqueness may surface as ValidationError.
                # Only treat the "__all__" unique collision as upsert; otherwise re-raise.
                if "__all__" not in getattr(e, "message_dict", {}):
                    raise

                try:
                    item = (
                        CartItem.objects.select_for_update()
                        .get(cart=cart, product=product)
                    )
                except CartItem.DoesNotExist:
                    # Rare race (e.g., concurrent delete). Retry insert once.
                    with transaction.atomic():
                        item = CartItem.objects.create(
                            cart=cart,
                            product=product,
                            quantity=quantity,
                            price_at_add_time=get_snapshot_gross_price(product),
                        )
                    created = True
                else:
                    item.quantity = quantity
                    item.save(update_fields=["quantity"])
                    created = False

            except IntegrityError:
                # Duplicate key at DB level -> fallback update
                try:
                    item = (
                        CartItem.objects.select_for_update()
                        .get(cart=cart, product=product)
                    )
                except CartItem.DoesNotExist:
                    # Race with delete: row disappeared, retry insert once
                    with transaction.atomic():
                        item = CartItem.objects.create(
                            cart=cart,
                            product=product,
                            quantity=quantity,
                            price_at_add_time=get_snapshot_gross_price(product),
                        )
                    created = True
                else:
                    item.quantity = quantity
                    item.save(update_fields=["quantity"])
                    created = False

        response = Response(
            CartItemSerializer(item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
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

    def _delete_cart_item_and_respond(
        self,
        *,
        cart,
        product_id: int,
        raw_token: str | None,
        request=None,
    ) -> Response:
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()

        # Ensure serializer sees the updated state
        cart.refresh_from_db()

        ctx = {"request": request} if request is not None else {}
        response = Response(
            CartSerializer(cart, context=ctx).data,
            status=status.HTTP_200_OK,
        )
        if raw_token:
            response.set_cookie(
                "cart_token",
                raw_token,
                **cart_token_cookie_kwargs(),
            )
        return response

    @extend_schema(
        tags=["Cart"],
        summary="Update cart item quantity",
        description="""Partially updates the quantity of a single cart item.

Business rules:
- `quantity` must be a positive integer.
- `quantity = 0` is a DELETE alias: the item is removed from the cart.
- If the item does not yet exist and `quantity > 0`, it is created (upsert semantics).
- Stock and product availability are validated.

Response is a full cart snapshot (same shape as `GET /cart/`).

HTTP semantics:
- 200 OK: existing item updated (or deleted via quantity=0)
- 201 Created: new item inserted
- 400 Bad Request: missing or invalid `quantity`
- 404 Not Found: product does not exist
- 409 Conflict: product unavailable or out of stock
""",
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
    def patch(self, request, product_id: int):
        serializer = CartItemUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]

        cart, _, raw_token = _resolve_or_create_cart(request)

        # quantity=0 is DELETE alias
        if quantity == 0:
            return self._delete_cart_item_and_respond(
                cart=cart, product_id=product_id, raw_token=raw_token, request=request
            )

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ProductNotFoundException()

        if not product.is_sellable():
            raise ProductUnavailableException()

        if quantity > product.stock_quantity:
            raise OutOfStockException()

        # Race-safe UPSERT:
        # - try INSERT in a savepoint (so DB errors don't poison the outer tx)
        # - if unique collision -> lock & UPDATE
        # - if DELETE wins mid-flight -> fallback get() may 404 -> retry once
        created = False
        item = None

        for _ in range(2):  # max 2 attempts is enough for delete-vs-put race
            with transaction.atomic():
                try:
                    # INSERT attempt in savepoint
                    with transaction.atomic():
                        item = CartItem.objects.create(
                            cart=cart,
                            product=product,
                            quantity=quantity,
                            price_at_add_time=get_snapshot_gross_price(product),
                        )
                    created = True
                    break

                except DjangoValidationError as e:
                    # Only treat unique collision as upsert fallback
                    if "__all__" not in getattr(e, "message_dict", {}):
                        raise

                except IntegrityError:
                    # DB-level unique collision -> fallback update
                    pass

                # Fallback: row should exist, lock it and update
                try:
                    item = (
                        CartItem.objects.select_for_update()
                        .get(cart=cart, product=product)
                    )
                except CartItem.DoesNotExist:
                    # DELETE won the race; retry loop -> try create again
                    continue

                item.quantity = quantity
                item.save(update_fields=["quantity"])
                created = False
                break

        # If after retries we still don't have item, something is genuinely wrong
        if item is None:
            # safest behavior: treat as internal error (should never happen)
            raise RuntimeError(
                "CartItem upsert failed unexpectedly (no item).")

        cart.refresh_from_db()

        response = Response(
            CartSerializer(cart, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
        if raw_token:
            response.set_cookie("cart_token", raw_token, **
                                cart_token_cookie_kwargs())
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
        return self._delete_cart_item_and_respond(
            cart=cart, product_id=product_id, raw_token=raw_token, request=request
        )


def _save_checkout_addresses_to_profile(user, checkout_data: dict) -> None:
    """
    Conditionally create Address records from checkout_data and update the
    user's CustomerProfile default addresses.

    Called after a successful checkout when ``save_to_profile=True``.
    Any error is logged and silently swallowed — callers MUST NOT propagate
    failures here to the checkout response.

    No-op protection
    ----------------
    Each side (shipping / billing) is only written when the effective checkout
    address differs from the current profile default.  This prevents
    unnecessary duplicate rows when the user checks out with prefilled data
    that already matches their saved profile address.

    Fields compared: ``first_name``, ``last_name``, ``street_line_1``,
    ``street_line_2``, ``city``, ``postal_code``, ``country``, ``phone``,
    ``company``, ``company_id``, ``vat_id``.

    When ``billing_same_as_shipping=True`` the billing address is derived
    from the shipping fields for comparison purposes.
    """
    from accounts.models import Address, CustomerProfile

    def _norm(v) -> str:
        return (v or "").strip()

    def _checkout_addr_matches(existing: Address, eff: dict) -> bool:
        """Return True when *existing* address equals *eff* on all checkout-
        captured fields (``first_name``, ``last_name``, ``street_line_1``,
        ``street_line_2``, ``city``, ``postal_code``, ``country``, ``phone``,
        ``company``, ``company_id``, ``vat_id``)."""
        return (
            _norm(existing.first_name) == _norm(eff["first_name"])
            and _norm(existing.last_name) == _norm(eff["last_name"])
            and _norm(existing.street_line_1) == _norm(eff["street_line_1"])
            and _norm(existing.street_line_2) == _norm(eff["street_line_2"])
            and _norm(existing.city) == _norm(eff["city"])
            and _norm(existing.postal_code) == _norm(eff["postal_code"])
            and _norm(str(existing.country)) == _norm(eff["country"])
            and _norm(existing.phone) == _norm(eff["phone"])
            and _norm(existing.company) == _norm(eff["company"])
            and _norm(existing.company_id) == _norm(eff["company_id"])
            and _norm(existing.vat_id) == _norm(eff["vat_id"])
        )

    profile, _ = CustomerProfile.objects.get_or_create(user=user)

    # Build effective shipping address dict
    eff_shipping = {
        "first_name": checkout_data["shipping_first_name"],
        "last_name": checkout_data["shipping_last_name"],
        "street_line_1": checkout_data["shipping_address_line1"],
        "street_line_2": checkout_data.get("shipping_address_line2", ""),
        "city": checkout_data["shipping_city"],
        "postal_code": checkout_data["shipping_postal_code"],
        "country": checkout_data["shipping_country"],
        "phone": checkout_data.get("shipping_phone", ""),
        "company": checkout_data.get("shipping_company", ""),
        "company_id": checkout_data.get("shipping_company_id", ""),
        "vat_id": checkout_data.get("shipping_vat_id", ""),
    }

    # Build effective billing address dict
    if checkout_data.get("billing_same_as_shipping", True):
        eff_billing = dict(eff_shipping)
    else:
        eff_billing = {
            "first_name": checkout_data.get("billing_first_name", ""),
            "last_name": checkout_data.get("billing_last_name", ""),
            "street_line_1": checkout_data.get("billing_address_line1", ""),
            "street_line_2": checkout_data.get("billing_address_line2", ""),
            "city": checkout_data.get("billing_city", ""),
            "postal_code": checkout_data.get("billing_postal_code", ""),
            "country": checkout_data.get("billing_country", ""),
            "phone": checkout_data.get("billing_phone", ""),
            "company": checkout_data.get("billing_company", ""),
            "company_id": checkout_data.get("billing_company_id", ""),
            "vat_id": checkout_data.get("billing_vat_id", ""),
        }

    update_fields = []

    # Shipping side: create new row only when address has actually changed
    existing_ship = profile.default_shipping_address
    if existing_ship is None or not _checkout_addr_matches(existing_ship, eff_shipping):
        new_ship = Address.objects.create(profile=profile, **eff_shipping)
        profile.default_shipping_address = new_ship
        update_fields.append("default_shipping_address")

    # Billing side: create new row only when address has actually changed
    existing_bill = profile.default_billing_address
    if existing_bill is None or not _checkout_addr_matches(existing_bill, eff_billing):
        new_bill = Address.objects.create(profile=profile, **eff_billing)
        profile.default_billing_address = new_bill
        update_fields.append("default_billing_address")

    if update_fields:
        profile.save(update_fields=update_fields)


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

        # Initialised here so the return statement always has a valid reference
        # even if the atomic block raises before assignment.
        price_change_data: dict | None = None

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

                # Resolve supplier configuration before creating the order.
                # This raises SupplierConfigurationError (HTTP 503) when the
                # required supplier setup is missing or ambiguous, preventing
                # order creation with incomplete supplier truth.
                supplier_snap = resolve_order_supplier_snapshot()

                order = Order(
                    user=request.user if request.user.is_authenticated else None,
                    customer_email=checkout_data["customer_email"],
                    shipping_first_name=checkout_data["shipping_first_name"],
                    shipping_last_name=checkout_data["shipping_last_name"],
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
                    billing_first_name=checkout_data.get("billing_first_name") or None,
                    billing_last_name=checkout_data.get("billing_last_name") or None,
                    billing_address_line1=checkout_data.get(
                        "billing_address_line1"),
                    billing_address_line2=checkout_data.get(
                        "billing_address_line2"),
                    billing_city=checkout_data.get("billing_city"),
                    billing_postal_code=checkout_data.get(
                        "billing_postal_code"),
                    billing_country=checkout_data.get("billing_country"),
                    billing_phone=checkout_data.get("billing_phone"),
                    shipping_company=checkout_data.get("shipping_company") or None,
                    shipping_company_id=checkout_data.get("shipping_company_id") or None,
                    shipping_vat_id=checkout_data.get("shipping_vat_id") or None,
                    billing_company=checkout_data.get("billing_company") or None,
                    billing_company_id=checkout_data.get("billing_company_id") or None,
                    billing_vat_id=checkout_data.get("billing_vat_id") or None,
                    # Supplier snapshot — immutable truth captured at checkout time.
                    supplier_name=supplier_snap.name,
                    supplier_company_id=supplier_snap.company_id,
                    supplier_vat_id=supplier_snap.vat_id,
                    supplier_email=supplier_snap.email,
                    supplier_phone=supplier_snap.phone,
                    supplier_street_line_1=supplier_snap.street_line_1,
                    supplier_street_line_2=supplier_snap.street_line_2,
                    supplier_city=supplier_snap.city,
                    supplier_postal_code=supplier_snap.postal_code,
                    supplier_country=supplier_snap.country,
                    supplier_bank_name=supplier_snap.bank_name,
                    supplier_account_number=supplier_snap.account_number,
                    supplier_iban=supplier_snap.iban,
                    supplier_swift=supplier_snap.swift,
                )
                try:
                    order.full_clean()
                except DjangoValidationError as exc:
                    raise DRFValidationError(exc.message_dict)
                order.save()

                if not request.user.is_authenticated:
                    try:
                        token = GuestOrderAccessService.issue_token(
                            order=order)
                        guest_url = generate_guest_access_url(
                            order=order,
                            token=token,
                        )
                        order_number = getattr(
                            order,
                            "order_number",
                            str(order.id),
                        )

                        def _enqueue() -> None:
                            enqueue_best_effort(
                                "notifications.jobs.send_guest_order_link",
                                recipient_email=order.customer_email,
                                order_number=order_number,
                                guest_order_url=guest_url,
                            )

                        transaction.on_commit(_enqueue)
                    except Exception:
                        NotificationErrorHandler.handle(
                            NotificationSendError(
                                code="GUEST_ORDER_EMAIL_INTENT_FAILED",
                                message="Failed to prepare guest order notification intent.",
                                context={
                                    "order_id": getattr(order, "id", None),
                                    "customer_email": getattr(order, "customer_email", None),
                                },
                            )
                        )

                # Phase 3: the current pricing pipeline is the authoritative
                # source for checkout pricing.  price_at_add_time is retained
                # on CartItem as the customer-visible gross baseline for
                # price-change detection (Phase 3 Slice 2).
                # Phase 4 / Slice 3: also resolves AUTO_APPLY order-level
                # promotions and populates cart_pricing.order_discount when one
                # is eligible.
                # Phase 4 / Slice 5B: when a CAMPAIGN_APPLY offer has been
                # claimed via session, it takes precedence over AUTO_APPLY.
                _checkout_campaign_offer = _get_claimed_campaign_offer(request)
                if _checkout_campaign_offer is not None:
                    cart_pricing = get_cart_pricing_with_campaign_offer(
                        cart, _checkout_campaign_offer
                    )
                else:
                    cart_pricing = get_cart_pricing_with_order_discount(cart)

                # Detect price changes before order items are created so that
                # the comparison uses the pre-checkout cart snapshot values.
                price_change_data = serialize_price_change_summary(
                    detect_price_changes(cart_pricing)
                )

                reservation_items = [
                    {"product_id": line.item.product_id, "quantity": line.item.quantity}
                    for line in cart_pricing.items
                ]

                for line in cart_pricing.items:
                    item = line.item
                    unit_pricing = line.unit_pricing

                    if unit_pricing is not None:
                        # Migrated product: use the tax-aware, promotion-aware
                        # pricing pipeline.  The discounted gross is the amount
                        # the customer pays per unit.
                        unit_gross = unit_pricing.discounted.gross.amount
                        line_total = (
                            unit_gross * Decimal(str(line.quantity))
                        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        discount_type = unit_pricing.discount.promotion_type or None
                        if discount_type == "PERCENT":
                            discount_value = unit_pricing.discount.percentage
                        elif discount_type == "FIXED":
                            discount_value = unit_pricing.discount.amount_gross.amount
                        else:
                            discount_type = None
                            discount_value = None
                        # Phase 3 snapshot fields — populated from pricing pipeline.
                        snap_unit_price_net = unit_pricing.discounted.net.amount
                        snap_unit_price_gross = unit_gross
                        snap_tax_amount = unit_pricing.discounted.tax.amount
                        snap_tax_rate = unit_pricing.discounted.tax_rate
                        snap_promo_code = unit_pricing.discount.promotion_code
                        snap_promo_type = unit_pricing.discount.promotion_type
                        snap_promo_discount_gross = (
                            unit_pricing.discount.amount_gross.amount
                            if unit_pricing.discount.promotion_type
                            else None
                        )
                        # Product + line total snapshots
                        snap_product_name = item.product.name
                        snap_line_total_net = (
                            snap_unit_price_net * Decimal(str(line.quantity))
                        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        snap_line_total_gross = line_total
                    else:
                        # Unmigrated product (price_net_amount not set): fall
                        # back to price_at_add_time as the gross unit price
                        # without any discount.  This path will be eliminated
                        # once all products are migrated to price_net_amount.
                        unit_gross = item.price_at_add_time
                        line_total = (
                            item.price_at_add_time * Decimal(str(line.quantity))
                        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        discount_type = None
                        discount_value = None
                        # Phase 3 snapshot fields — unavailable for unmigrated products.
                        snap_unit_price_net = None
                        snap_unit_price_gross = None
                        snap_tax_amount = None
                        snap_tax_rate = None
                        snap_promo_code = None
                        snap_promo_type = None
                        snap_promo_discount_gross = None
                        # Product + line total snapshots (partial for unmigrated)
                        snap_product_name = item.product.name
                        snap_line_total_net = None
                        snap_line_total_gross = line_total

                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price_at_order_time=line_total,
                        unit_price_at_order_time=unit_gross,
                        line_total_at_order_time=line_total,
                        applied_discount_type_at_order_time=discount_type,
                        applied_discount_value_at_order_time=discount_value,
                        # Phase 3 snapshot fields
                        unit_price_net_at_order_time=snap_unit_price_net,
                        unit_price_gross_at_order_time=snap_unit_price_gross,
                        tax_amount_at_order_time=snap_tax_amount,
                        tax_rate_at_order_time=snap_tax_rate,
                        promotion_code_at_order_time=snap_promo_code,
                        promotion_type_at_order_time=snap_promo_type,
                        promotion_discount_gross_at_order_time=snap_promo_discount_gross,
                        # Phase 3 Slice 5: product name + line total snapshots
                        product_name_at_order_time=snap_product_name,
                        line_total_net_at_order_time=snap_line_total_net,
                        line_total_gross_at_order_time=snap_line_total_gross,
                    )

                # Phase 3 / 4: persist order-level totals snapshot.
                # Phase 4 / Slice 3: when an order-level discount is applied,
                # subtotal_gross and total_tax are adjusted to the post-discount
                # values returned by the VAT allocation engine.
                od = cart_pricing.order_discount
                if od is not None:
                    _subtotal_gross = od.total_gross_after.amount
                    _total_tax = od.total_tax_after.amount
                    _order_discount_gross = od.gross_reduction.amount
                    _order_promotion_code = od.promotion_code
                else:
                    _subtotal_gross = cart_pricing.subtotal_discounted.amount
                    _total_tax = cart_pricing.total_tax.amount
                    _order_discount_gross = None
                    _order_promotion_code = None

                order.subtotal_gross = _subtotal_gross
                order.subtotal_net = (
                    _subtotal_gross - _total_tax
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                order.total_tax = _total_tax
                order.total_discount = (
                    cart_pricing.total_discount.amount
                    + (_order_discount_gross or Decimal("0"))
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                order.order_discount_gross = _order_discount_gross
                order.order_promotion_code = _order_promotion_code
                order.currency = cart_pricing.currency
                order.save(
                    update_fields=[
                        "subtotal_net",
                        "subtotal_gross",
                        "total_tax",
                        "total_discount",
                        "order_discount_gross",
                        "order_promotion_code",
                        "currency",
                    ]
                )

                reserve_for_checkout(order=order, items=reservation_items)

                cart.status = Cart.Status.CONVERTED
                cart.save()

                # Phase 4 / Offer status: mark the campaign offer as REDEEMED
                # only when it was the winning promotion actually applied to
                # this order (not when an AUTO_APPLY promotion outbid it).
                # The forward-only guard (status__in) prevents EXPIRED or other
                # terminal states from being silently overwritten.
                if (
                    _checkout_campaign_offer is not None
                    and od is not None
                    and _order_promotion_code == _checkout_campaign_offer.promotion.code
                ):
                    Offer.objects.filter(
                        pk=_checkout_campaign_offer.pk,
                        status__in=[
                            OfferStatus.CREATED,
                            OfferStatus.DELIVERED,
                            OfferStatus.CLAIMED,
                        ],
                    ).update(status=OfferStatus.REDEEMED)

        except APIException:
            raise

        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict)

        except Exception:
            # atomic block guarantees rollback
            raise CheckoutFailedException()

        # ── Payment initiation ───────────────────────────────────────────────
        # Called AFTER the order creation transaction has committed so that
        # the DB lock is released before any outbound HTTP calls are made
        # (e.g. AcquireMock invoice creation for CARD).
        # If initiation fails for any reason the order remains in CREATED
        # status and can be retried; it is NOT rolled back because the
        # transaction has already committed.
        payment = PaymentOrchestrationService.start_payment(
            order=order,
            payment_method=checkout_data["payment_method"],
            extra={"callback_base_url": request.build_absolute_uri("/")},
        )

        # ── Optional: save checkout addresses to the user's profile ─────────
        if checkout_data.get("save_to_profile") and request.user.is_authenticated:
            try:
                _save_checkout_addresses_to_profile(request.user, checkout_data)
            except Exception:
                logger.exception(
                    "Failed to save checkout addresses to profile for user %s",
                    request.user.pk,
                )

        response_data = dict(CartCheckoutResponseSerializer(order).data)
        response_data["price_change"] = price_change_data
        # Provider-agnostic payment initiation result for the frontend.
        # REDIRECT: frontend must redirect the customer to redirect_url.
        # DIRECT:   checkout is complete; no redirect required (e.g. COD).
        response_data["payment_initiation"] = PaymentInitiationSerializer({
            "payment_id": payment.pk,
            "payment_flow": "REDIRECT" if payment.redirect_url else "DIRECT",
            "redirect_url": payment.redirect_url,
        }).data
        # Phase 4 / Slice 5B: clear the campaign offer cookie after a
        # successful checkout so the same offer is not applied again.
        checkout_response = Response(response_data, status=status.HTTP_201_CREATED)
        _clear_campaign_offer_cookie(checkout_response)
        return checkout_response


class CartCheckoutPreflightView(APIView):
    """Lightweight checkout preflight — price-change check without creating an order.

    Resolves the current cart pricing and compares each item's
    ``price_at_add_time`` (gross baseline snapshotted at add-to-cart time)
    against the current effective gross from the pricing pipeline.

    Returns the same ``price_change`` payload shape used by the checkout
    endpoint, enabling the frontend to surface messaging at checkout entry
    (Step 1) before the customer commits.

    Endpoint behaviour
    ------------------
    - Read-only.  No DB writes.
    - 200: active cart found — always returns the payload (severity may be NONE).
    - 404: no ACTIVE cart exists for the request context.

    HTTP method: GET
    URL:         /api/v1/cart/checkout/preflight/
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Cart Checkout"],
        summary="Checkout preflight — price-change check",
        description="""
Compares the current effective pricing for every cart item against the
gross unit price snapshotted at add-to-cart time and returns a structured
price-change summary.

Use this endpoint when rendering checkout Step 1 to surface price-change
messaging *before* the customer fills in their details.

- `severity = NONE` — no action required.
- `severity = INFO` — prices changed slightly; show a non-intrusive toast.
- `severity = WARNING` — prices changed significantly; show an inline banner.

No order is created. The endpoint is safe to call multiple times.
""",
        parameters=CART_TOKEN_PARAMETERS,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "price_change": {"type": "object"},
                },
            },
            404: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        cart = _get_active_cart_for_request(request)
        if cart is None:
            raise NoActiveCartException()

        cart_pricing = get_cart_pricing(cart)
        summary = detect_price_changes(cart_pricing)
        payload = serialize_price_change_summary(summary)
        return Response({"price_change": payload}, status=status.HTTP_200_OK)
