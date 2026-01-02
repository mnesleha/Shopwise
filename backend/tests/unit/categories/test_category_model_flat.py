import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from categories.models import Category


@pytest.mark.django_db
def test_category_name_is_required():
    c = Category(name="")
    with pytest.raises(ValidationError):
        c.full_clean()


@pytest.mark.django_db
def test_category_name_must_be_globally_unique_db():
    Category.objects.create(name="Electronics")
    with pytest.raises(IntegrityError):
        Category.objects.create(name="Electronics")


@pytest.mark.django_db
def test_category_name_must_be_globally_unique_validation():
    Category.objects.create(name="Electronics")
    c = Category(name="Electronics")
    with pytest.raises(ValidationError):
        c.full_clean()
