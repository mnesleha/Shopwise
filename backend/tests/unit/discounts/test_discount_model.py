import pytest
from django.utils.timezone import now, timedelta


@pytest.mark.django_db
def test_discount_is_valid_only_within_date_range():
    from discounts.models import Discount

    discount = Discount.objects.create(
        name="Summer Sale",
        discount_type="PERCENT",
        value=10,
        valid_from=now() - timedelta(days=1),
        valid_to=now() + timedelta(days=1),
        is_active=True,
    )

    assert discount.is_valid() is True
