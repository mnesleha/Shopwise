import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
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


@pytest.mark.django_db
def test_category_detail_not_found_returns_404(auth_client):
    r = auth_client.get("/api/v1/categories/999999/")
    assert r.status_code == 404


@pytest.mark.django_db
def test_categories_response_has_no_legacy_hierarchy_fields(auth_client):
    Category.objects.create(name="Electronics")

    r = auth_client.get("/api/v1/categories/?include=children&include=parent")
    assert r.status_code == 200
    data = r.json()

    for item in data:
        assert "children" not in item
        assert "parent" not in item
        assert "is_parent" not in item


@pytest.mark.django_db
def test_category_detail_has_no_legacy_hierarchy_fields(auth_client):
    c = Category.objects.create(name="Electronics")

    r = auth_client.get(f"/api/v1/categories/{c.id}/?include=children")
    assert r.status_code == 200
    item = r.json()

    assert "children" not in item
    assert "parent" not in item
    assert "is_parent" not in item
