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
    Exposes only the id and the nullable default-address FK IDs.
    Validates that chosen default addresses belong to the authenticated user's profile.
    """

    default_shipping_address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.none(),  # overridden in __init__
        allow_null=True,
        required=False,
    )
    default_billing_address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.none(),  # overridden in __init__
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            profile = getattr(request.user, "customer_profile", None)
            if profile is not None:
                own_qs = Address.objects.filter(profile=profile)
                self.fields["default_shipping_address"].queryset = own_qs
                self.fields["default_billing_address"].queryset = own_qs
