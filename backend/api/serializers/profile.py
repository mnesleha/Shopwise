from django_countries.serializer_fields import CountryField
from rest_framework import serializers

from accounts.models import Address, CustomerProfile


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for Address instances.
    The `profile` ownership is never exposed or accepted from clients;
    it is assigned automatically in the view layer from the request user.
    """

    # Serialize country as a plain ISO 3166-1 alpha-2 code string (no dict).
    # This preserves the existing API contract while benefiting from
    # django-countries validation on the model layer.
    country = CountryField()

    class Meta:
        model = Address
        fields = [
            "id",
            "first_name",
            "last_name",
            "street_line_1",
            "street_line_2",
            "city",
            "postal_code",
            "country",
            "company",
            "vat_id",
        ]
        read_only_fields = ["id"]


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for CustomerProfile.

    Exposes: id, default_shipping_address (FK id), default_billing_address (FK id).

    Ownership validation is done via field-level validators that consult
    ``context["request"].user``; no DB queries happen in ``__init__``.
    """

    # Accept any Address PK; ownership is enforced in the field validators below.
    default_shipping_address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        allow_null=True,
        required=False,
    )
    default_billing_address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = CustomerProfile
        fields = [
            "id",
            "default_shipping_address",
            "default_billing_address",
        ]
        read_only_fields = ["id"]

    # ------------------------------------------------------------------
    # Ownership validators
    # ------------------------------------------------------------------

    def _assert_address_belongs_to_user(
        self, address: Address, field_name: str
    ) -> None:
        """
        Raise ValidationError if *address* does not belong to the authenticated
        user's saved CustomerProfile.

        Uses request.user rather than the serializer instance so that the check
        is independent of whether the profile object was saved at the time the
        serializer was constructed.
        """
        request = self.context.get("request")
        if address is None or request is None:
            return

        try:
            profile = CustomerProfile.objects.get(user=request.user)
        except CustomerProfile.DoesNotExist:
            # User has no profile yet → they cannot own any address.
            raise serializers.ValidationError(
                {field_name: "This address does not belong to your profile."}
            )

        if address.profile_id != profile.pk:
            raise serializers.ValidationError(
                {field_name: "This address does not belong to your profile."}
            )

    def validate_default_shipping_address(self, value: Address | None) -> Address | None:
        if value is not None:
            self._assert_address_belongs_to_user(value, "default_shipping_address")
        return value

    def validate_default_billing_address(self, value: Address | None) -> Address | None:
        if value is not None:
            self._assert_address_belongs_to_user(value, "default_billing_address")
        return value
