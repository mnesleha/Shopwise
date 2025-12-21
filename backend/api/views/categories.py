from rest_framework.viewsets import ReadOnlyModelViewSet
from categories.models import Category
from api.serializers.category import CategorySerializer


class CategoryViewSet(ReadOnlyModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(
            is_parent=True
        ).prefetch_related("children")
