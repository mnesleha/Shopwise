import pytest
from django.core.exceptions import ValidationError
from categories.models import Category


@pytest.mark.django_db
def test_category_without_name_is_invalid():

    category = Category(name="")

    with pytest.raises(ValidationError):
        category.full_clean()
