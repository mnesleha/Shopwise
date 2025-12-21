from rest_framework import serializers
from categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "is_parent",
            "children",
        ]

    def get_children(self, obj):
        children = obj.children.all()
        return CategorySerializer(children, many=True).data
