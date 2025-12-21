import pytest
from rest_framework.test import APIClient
from categories.models import Category


@pytest.mark.django_db
def test_categories_list_returns_tree_structure():
    parent = Category.objects.create(
        name="Electronics",
        is_parent=True,
    )

    child = Category.objects.create(
        name="Phones",
        is_parent=False,
        parent=parent,
    )

    client = APIClient()
    response = client.get("/api/v1/categories/")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1

    parent_data = data[0]
    assert parent_data["name"] == "Electronics"
    assert parent_data["is_parent"] is True
    assert len(parent_data["children"]) == 1

    child_data = parent_data["children"][0]
    assert child_data["name"] == "Phones"
    assert child_data["is_parent"] is False
    assert child_data["children"] == []
