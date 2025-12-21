from rest_framework.viewsets import ReadOnlyModelViewSet
from products.models import Product
from api.serializers.product import ProductSerializer


class ProductViewSet(ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(
            is_active=True,
            stock_quantity__gt=0,
        )
