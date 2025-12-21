from rest_framework.viewsets import ReadOnlyModelViewSet
from discounts.models import Discount
from api.serializers.discount import DiscountSerializer
from django.utils.timezone import now


class DiscountViewSet(ReadOnlyModelViewSet):
    serializer_class = DiscountSerializer

    def get_queryset(self):
        today = now().date()
        return Discount.objects.filter(
            is_active=True,
            valid_from__lte=today,
            valid_to__gte=today,
        ).select_related("product")
