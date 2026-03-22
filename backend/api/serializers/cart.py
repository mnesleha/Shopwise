from rest_framework import serializers

from carts.models import Cart, CartItem
from products.models import Product
from api.serializers.order import OrderResponseSerializer


# ---------------------------------------------------------------------------
# Cart pricing serializers
# ---------------------------------------------------------------------------


class CartTotalsSerializer(serializers.Serializer):
    """Serialises a ``CartTotalsResult`` — backend-computed cart-level totals.

    All monetary amounts are decimal strings.  Tax is calculated from the
    post-discount net, consistent with catalogue pricing semantics.

    Shape::

        {
          "subtotal_undiscounted": "...",
          "subtotal_discounted":   "...",
          "total_discount":        "...",
          "total_tax":             "...",
          "total_gross":           "...",
          "currency":              "EUR",
          "item_count":            3
        }
    """

    subtotal_undiscounted = serializers.SerializerMethodField(
        help_text="Sum of undiscounted_gross × quantity for all items."
    )
    subtotal_discounted = serializers.SerializerMethodField(
        help_text="Sum of discounted_gross × quantity (equals total_gross)."
    )
    total_discount = serializers.SerializerMethodField(
        help_text="subtotal_undiscounted − subtotal_discounted (≥ 0)."
    )
    total_tax = serializers.SerializerMethodField(
        help_text="Sum of discounted_tax × quantity."
    )
    total_gross = serializers.SerializerMethodField(
        help_text="Total amount payable (= subtotal_discounted)."
    )
    currency = serializers.SerializerMethodField(
        help_text="ISO 4217 currency code."
    )
    item_count = serializers.SerializerMethodField(
        help_text="Total units in the cart (sum of quantities)."
    )

    def get_subtotal_undiscounted(self, obj) -> str:
        return str(obj.subtotal_undiscounted.amount)

    def get_subtotal_discounted(self, obj) -> str:
        return str(obj.subtotal_discounted.amount)

    def get_total_discount(self, obj) -> str:
        return str(obj.total_discount.amount)

    def get_total_tax(self, obj) -> str:
        return str(obj.total_tax.amount)

    def get_total_gross(self, obj) -> str:
        return str(obj.total_gross.amount)

    def get_currency(self, obj) -> str:
        return obj.currency

    def get_item_count(self, obj) -> int:
        return obj.item_count

    # ------------------------------------------------------------------
    # Phase 4 / Slice 3: order-level discount fields
    # ------------------------------------------------------------------

    order_discount_applied = serializers.SerializerMethodField(
        help_text="True when an AUTO_APPLY order-level promotion is applied."
    )
    order_discount_amount = serializers.SerializerMethodField(
        help_text="Gross discount amount from the order-level promotion, or null."
    )
    order_discount_promotion_code = serializers.SerializerMethodField(
        help_text="Code of the applied order promotion, or null."
    )
    order_discount_promotion_name = serializers.SerializerMethodField(
        help_text="Name of the applied order promotion, or null."
    )
    total_gross_after_order_discount = serializers.SerializerMethodField(
        help_text="Total gross payable after order-level discount, or null when no discount."
    )
    total_tax_after_order_discount = serializers.SerializerMethodField(
        help_text="Total VAT after order-level discount reallocation, or null when no discount."
    )

    # ------------------------------------------------------------------
    # Phase 4 / Slice 4: threshold reward progress
    # ------------------------------------------------------------------

    threshold_reward = serializers.SerializerMethodField(
        help_text=(
            "Progress towards a threshold-based order reward, or null when "
            "no such promotion exists.  Shape: {is_unlocked, promotion_name, "
            "threshold, current_basis, remaining, currency}."
        )
    )

    def get_order_discount_applied(self, obj) -> bool:
        return obj.order_discount is not None

    def get_order_discount_amount(self, obj):
        if obj.order_discount is None:
            return None
        return str(obj.order_discount.gross_reduction.amount)

    def get_order_discount_promotion_code(self, obj):
        if obj.order_discount is None:
            return None
        return obj.order_discount.promotion_code

    def get_order_discount_promotion_name(self, obj):
        if obj.order_discount is None:
            return None
        return obj.order_discount.promotion_name

    def get_total_gross_after_order_discount(self, obj):
        if obj.order_discount is None:
            return None
        return str(obj.order_discount.total_gross_after.amount)

    def get_total_tax_after_order_discount(self, obj):
        if obj.order_discount is None:
            return None
        return str(obj.order_discount.total_tax_after.amount)

    def get_threshold_reward(self, obj) -> dict | None:
        tr = obj.threshold_reward
        if tr is None:
            return None
        return {
            "is_unlocked": tr.is_unlocked,
            "promotion_name": tr.promotion_name,
            "threshold": str(tr.threshold),
            "current_basis": str(tr.current_basis),
            "remaining": str(tr.remaining),
            "currency": tr.currency,
        }

    # ------------------------------------------------------------------
    # Phase 4 / Slice 5C: order discount decision engine
    # ------------------------------------------------------------------

    campaign_outcome = serializers.SerializerMethodField(
        help_text=(
            "Campaign offer outcome: 'APPLIED' when the claimed offer is the "
            "current winner, 'SUPERSEDED' when a better auto-apply promotion "
            "is active, or null when no campaign offer context exists."
        )
    )
    order_discount_next_upgrade = serializers.SerializerMethodField(
        help_text=(
            "Next meaningful order-level winner transition, or null.  Shape: "
            "{threshold, remaining, promotion_name, currency}."
        )
    )

    def get_campaign_outcome(self, obj) -> str | None:
        return getattr(obj, "campaign_outcome", None)

    def get_order_discount_next_upgrade(self, obj) -> dict | None:
        upg = getattr(obj, "order_discount_upgrade", None)
        if upg is None:
            return None
        return {
            "threshold": str(upg.threshold),
            "remaining": str(upg.remaining),
            "promotion_name": upg.promotion_name,
            "currency": upg.currency,
        }


class CartItemProductSerializer(serializers.ModelSerializer):
    """
    Minimal product representation embedded in cart responses.

    Rationale:
    - Improves frontend usability (no extra lookup required).
    - Keeps API responses self-describing for E2E tests (Postman / pytest).
    """

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = CartItemProductSerializer(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "quantity",
            "price_at_add_time",
        ]


class CartSerializer(serializers.ModelSerializer):
    # NOTE: items is overridden as a SerializerMethodField so that the cart
    # pricing pipeline is executed exactly once (inside _get_cart_pricing) and
    # the resulting per-item pricing data is injected into each item dict
    # without an extra DB round-trip.
    items = serializers.SerializerMethodField()
    totals = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "status",
            "items",
            "totals",
        ]

    # ------------------------------------------------------------------
    # Pricing cache helpers
    # ------------------------------------------------------------------

    def _get_cart_pricing(self, instance):
        """Compute cart pricing once per serializer invocation and cache it.

        Phase 4 / Slice 5B: when a ``request`` is present in the serializer
        context and the session contains a claimed CAMPAIGN_APPLY offer, the
        campaign offer pricing function is used instead of the AUTO_APPLY
        resolver, so the discount is reflected in the cart response.
        """
        if not hasattr(self, "_cart_pricing_cache"):
            from carts.services.pricing import (  # noqa: PLC0415
                get_cart_pricing_with_campaign_offer,
                get_cart_pricing_with_order_discount,
            )
            from api.services.campaign_offer_session import (  # noqa: PLC0415
                get_claimed_campaign_offer,
            )

            request = self.context.get("request")
            claimed_offer = get_claimed_campaign_offer(request)
            if claimed_offer is not None:
                self._cart_pricing_cache = get_cart_pricing_with_campaign_offer(
                    instance, claimed_offer
                )
            else:
                self._cart_pricing_cache = get_cart_pricing_with_order_discount(instance)
        return self._cart_pricing_cache

    # ------------------------------------------------------------------
    # SerializerMethodField implementations
    # ------------------------------------------------------------------

    def get_items(self, instance):
        """Return cart items enriched with per-item pricing breakdown."""
        from api.serializers.product import ProductPricingResultSerializer  # noqa: PLC0415

        cart_pricing = self._get_cart_pricing(instance)
        result = []
        for line in cart_pricing.items:
            item_data = dict(CartItemSerializer(line.item).data)
            item_data["pricing"] = (
                ProductPricingResultSerializer(line.unit_pricing).data
                if line.unit_pricing is not None
                else None
            )
            result.append(item_data)
        return result

    def get_totals(self, instance):
        """Return backend-computed cart-level pricing totals."""
        return CartTotalsSerializer(self._get_cart_pricing(instance)).data


class CartItemCreateRequestSerializer(serializers.Serializer):
    """
    OpenAPI request schema for adding an item to the cart.

    This serializer is used for documentation and validation
    of the request body, not for saving data.
    """
    product_id = serializers.IntegerField(
        help_text="ID of the product to add to the cart"
    )
    quantity = serializers.IntegerField(
        min_value=1,
        help_text="Quantity must be greater than zero"
    )


class CartItemUpdateRequestSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)


class CartCheckoutRequestSerializer(serializers.Serializer):
    customer_email = serializers.EmailField()
    shipping_first_name = serializers.CharField()
    shipping_last_name = serializers.CharField()
    shipping_address_line1 = serializers.CharField()
    shipping_address_line2 = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    shipping_city = serializers.CharField()
    shipping_postal_code = serializers.CharField()
    shipping_country = serializers.CharField()
    shipping_phone = serializers.CharField()
    billing_same_as_shipping = serializers.BooleanField(default=True)
    billing_first_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_last_name = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_address_line1 = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_address_line2 = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_city = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_postal_code = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_country = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    billing_phone = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    save_to_profile = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs):
        if attrs.get("billing_same_as_shipping") is False:
            required_fields = [
                "billing_first_name",
                "billing_last_name",
                "billing_address_line1",
                "billing_city",
                "billing_postal_code",
                "billing_country",
            ]
            errors = {}
            for field in required_fields:
                value = attrs.get(field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    errors[field] = ["This field is required."]
            if errors:
                raise serializers.ValidationError(errors)
        return attrs


class CartCheckoutResponseSerializer(OrderResponseSerializer):
    """Checkout response shares the same contract as Orders endpoints."""


class CartMergeWarningSerializer(serializers.Serializer):
    """Describes a single adjustment made during cart merge (e.g. stock cap)."""

    code = serializers.CharField()
    product_id = serializers.IntegerField()
    requested = serializers.IntegerField()
    applied = serializers.IntegerField()


class CartMergeReportSerializer(serializers.Serializer):
    """
    Full report returned by POST /cart/merge/.

    ``performed`` is False when there was no guest token to process (NOOP).
    ``result`` is one of: "NOOP" | "ADOPTED" | "MERGED".
    Warning codes: "STOCK_ADJUSTED".
    ``winning_offer_token`` is the campaign offer token that should be active
    after the merge (None when no valid offer survived).
    """

    performed = serializers.BooleanField()
    result = serializers.ChoiceField(choices=["NOOP", "ADOPTED", "MERGED"])
    items_added = serializers.IntegerField()
    items_updated = serializers.IntegerField()
    items_removed = serializers.IntegerField()
    warnings = CartMergeWarningSerializer(many=True)
    winning_offer_token = serializers.CharField(allow_null=True, default=None)
