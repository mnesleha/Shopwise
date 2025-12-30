from api.exceptions.base import ConflictException, NotFoundException, ValidationException

# --- Cart Items exceptions ---


class CartItemInvalidQuantityException(ValidationException):
    default_code = "invalid_quantity"
    default_detail = "Quantity must be greater than zero."


class CartItemMissingFieldException(ValidationException):
    default_code = "missing_fields"
    default_detail = "product_id and quantity are required."


class CartItemQuantityNotIntegerException(ValidationException):
    default_code = "quantity_not_integer"
    default_detail = "Quantity must be an integer."


class ProductUnavailableException(ConflictException):
    default_code = "product_unavailable"
    default_detail = "Product is currently unavailable."


class ProductNotFoundException(NotFoundException):
    default_code = "product_not_found"
    default_detail = "Referenced product does not exist."

# --- Cart Checkout exceptions ---


class NoActiveCartException(NotFoundException):
    default_detail = "No active cart to checkout."
    default_code = "no_active_cart"


class CartEmptyException(ValidationException):
    default_detail = "Cart is empty."
    default_code = "cart_empty"


class CartAlreadyCheckedOutException(ConflictException):
    default_detail = "Cart has already been checked out."
    default_code = "cart_already_checked_out"


class CheckoutFailedException(ConflictException):
    default_detail = "Checkout failed. Please retry."
    default_code = "checkout_failed"
