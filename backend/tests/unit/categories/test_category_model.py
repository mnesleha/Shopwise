import pytest
from django.core.exceptions import ValidationError
from categories.models import Category


@pytest.mark.django_db
def test_category_can_have_parent():

    parent = Category.objects.create(name="Electronics")
    child = Category.objects.create(name="Phones", parent=parent)

    assert child.parent == parent


@pytest.mark.django_db
def test_category_without_name_is_invalid():

    category = Category(name="")

    with pytest.raises(ValidationError):
        category.full_clean()


@pytest.mark.django_db
def test_category_name_must_be_unique_within_same_parent():

    parent = Category.objects.create(name="Electronics")

    Category.objects.create(name="Phones", parent=parent)

    duplicate = Category(
        name="Phones",
        parent=parent,
    )

    with pytest.raises(ValidationError):
        duplicate.full_clean()


@pytest.mark.django_db
def test_leaf_category_must_have_parent():

    category = Category(name="Phones", is_parent=False)

    with pytest.raises(ValidationError):
        category.full_clean()


@pytest.mark.django_db
def test_parent_category_cannot_have_parent():

    parent = Category.objects.create(name="Electronics", is_parent=True)

    category = Category(
        name="Sub",
        is_parent=True,
        parent=parent,
    )

    with pytest.raises(ValidationError):
        category.full_clean()
