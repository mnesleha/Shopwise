import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from carts.models import Cart, CartItem
from products.models import Product
from carts.models import Cart


@pytest.mark.django_db
def test_cart_item_quantity_must_be_positive():
    User = get_user_model()
    user = User.objects.create_user(email="u1@example.com", password="pass")
    cart = Cart.objects.create(user=user)

    product = Product.objects.create(
        name="Product",
        price=100,
        stock_quantity=10,
        is_active=True,
    )

    with pytest.raises(Exception):
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=0,
            price_at_add_time=product.price,
        )


@pytest.mark.django_db
def test_cart_allows_anonymous_user_null():
    cart = Cart.objects.create(user=None, status=Cart.Status.ACTIVE)
    assert cart.user is None
    assert cart.status == Cart.Status.ACTIVE


@pytest.mark.django_db
def test_user_can_have_only_one_active_cart_but_rule_does_not_apply_to_anonymous():
    User = get_user_model()
    user = User.objects.create_user(
        email="u2@example.com", password="Passw0rd!123")

    Cart.objects.create(user=user, status=Cart.Status.ACTIVE)

    with pytest.raises(ValidationError):
        Cart.objects.create(user=user, status=Cart.Status.ACTIVE)

    # Anonymous ACTIVE carts are allowed to coexist
    Cart.objects.create(user=None, status=Cart.Status.ACTIVE)
    Cart.objects.create(user=None, status=Cart.Status.ACTIVE)


@pytest.mark.django_db
def test_converted_cart_does_not_count_as_active_for_uniqueness():
    User = get_user_model()
    user = User.objects.create_user(
        email="u3@example.com", password="Passw0rd!123")

    Cart.objects.create(user=user, status=Cart.Status.CONVERTED)
    # should be allowed
    Cart.objects.create(user=user, status=Cart.Status.ACTIVE)


@pytest.mark.django_db
def test_anonymous_token_hash_is_unique_when_present():
    Cart.objects.create(user=None, status=Cart.Status.ACTIVE,
                        anonymous_token_hash="h1")

    with pytest.raises(ValidationError):
        Cart.objects.create(
            user=None, status=Cart.Status.ACTIVE, anonymous_token_hash="h1")


@pytest.mark.django_db
def test_adopt_flow_cart_stays_active_and_token_is_cleared():
    """
    Adoption: anonymous cart becomes user's ACTIVE cart.
    It must NOT become MERGED and must not set merged_into_cart.
    """
    User = get_user_model()
    user = User.objects.create_user(
        email="adopt@example.com", password="Passw0rd!123")

    cart = Cart.objects.create(
        user=None, status=Cart.Status.ACTIVE, anonymous_token_hash="h_adopt")

    # Adopt
    cart.user = user
    cart.anonymous_token_hash = None
    cart.save()

    cart.refresh_from_db()
    assert cart.user_id == user.id
    assert cart.status == Cart.Status.ACTIVE
    assert cart.anonymous_token_hash is None
    assert cart.merged_into_cart_id is None
    assert cart.merged_at is None


@pytest.mark.django_db
def test_merge_flow_requires_merged_into_cart_and_merged_at_and_sets_status_merged():
    """
    Merge: anonymous cart becomes terminal MERGED, references the target user cart.
    """
    User = get_user_model()
    user = User.objects.create_user(
        email="merge@example.com", password="Passw0rd!123")

    user_cart = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    anon_cart = Cart.objects.create(
        user=None, status=Cart.Status.ACTIVE, anonymous_token_hash="h_merge")

    anon_cart.status = Cart.Status.MERGED
    anon_cart.anonymous_token_hash = None
    anon_cart.merged_into_cart = user_cart
    anon_cart.merged_at = timezone.now()
    anon_cart.full_clean()
    anon_cart.save()

    anon_cart.refresh_from_db()
    assert anon_cart.status == Cart.Status.MERGED
    assert anon_cart.anonymous_token_hash is None
    assert anon_cart.merged_into_cart_id == user_cart.id
    assert anon_cart.merged_at is not None


@pytest.mark.django_db
def test_merged_cart_cannot_have_token_hash():
    """
    Invariant: MERGED carts must not be addressable by token.
    """
    anon_cart = Cart.objects.create(
        user=None, status=Cart.Status.ACTIVE, anonymous_token_hash="h_x")

    anon_cart.status = Cart.Status.MERGED
    # violating invariant: token still set
    with pytest.raises(ValidationError):
        anon_cart.full_clean()
        anon_cart.save()


@pytest.mark.django_db
def test_merged_cart_must_reference_target_cart():
    """
    Invariant: MERGED carts must reference merged_into_cart.
    """
    anon_cart = Cart.objects.create(
        user=None, status=Cart.Status.ACTIVE, anonymous_token_hash="h_y")

    anon_cart.status = Cart.Status.MERGED
    anon_cart.anonymous_token_hash = None
    anon_cart.merged_at = timezone.now()

    with pytest.raises(ValidationError):
        anon_cart.full_clean()
        anon_cart.save()


@pytest.mark.django_db
def test_active_cart_cannot_have_merge_metadata(user):
    """
    Invariant: Only MERGED carts may have merged_into_cart / merged_at set.
    ACTIVE carts must raise ValidationError if merge metadata is present.
    """
    active = Cart.objects.create(user=user, status=Cart.Status.ACTIVE)
    target = Cart.objects.create(user=user, status=Cart.Status.CONVERTED)

    active.merged_into_cart = target
    active.merged_at = timezone.now()

    with pytest.raises(ValidationError):
        active.full_clean()
