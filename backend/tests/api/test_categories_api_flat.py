import pytest
from categories.models import Category


@pytest.mark.django_db
def test_categories_list_is_flat(auth_client):
    # Arrange
    Category.objects.create(name="Electronics")
    Category.objects.create(name="Books")

    # Act
    r = auth_client.get("/api/v1/categories/")

    # Assert
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Contract: flat items only
    for item in data:
        assert set(item.keys()) == {"id", "name"}
        assert isinstance(item["id"], int)
        assert isinstance(item["name"], str)


@pytest.mark.django_db
def test_category_detail_is_flat(auth_client):
    # Arrange
    c = Category.objects.create(name="Home")

    # Act
    r = auth_client.get(f"/api/v1/categories/{c.id}/")

    # Assert
    assert r.status_code == 200
    item = r.json()
    assert set(item.keys()) == {"id", "name"}
    assert item["id"] == c.id
    assert item["name"] == "Home"
