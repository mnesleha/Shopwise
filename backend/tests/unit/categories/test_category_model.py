import pytest
from django.core.exceptions import ValidationError


@pytest.mark.django_db
def test_category_can_have_parent():
    from categories.models import Category

    parent = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Phones", parent=parent)

    assert child.parent == parent
