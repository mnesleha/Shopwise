from api.exceptions.base import ConflictException, NotFoundException, ValidationException

# --- Cart Items exceptions ---


class CartItemInvalidQuantityException(ValidationException):
    default_code = "INVALID_QUANTITY"
    default_detail = "Quantity must be greater than zero."


class CartItemMissingFieldException(ValidationException):
    default_code = "MISSING_FIELDS"
    default_detail = "product_id and quantity are required."


class CartItemQuantityNotIntegerException(ValidationException):
    default_code = "QUANTITY_NOT_INTEGER"
    default_detail = "Quantity must be an integer."


class ProductUnavailableException(ConflictException):
    default_code = "PRODUCT_UNAVAILABLE"
    default_detail = "Product is currently unavailable."


class ProductNotFoundException(NotFoundException):
    default_code = "PRODUCT_NOT_FOUND"
    default_detail = "Referenced product does not exist."

# --- Cart Checkout exceptions ---


class NoActiveCartException(NotFoundException):
    default_detail = "No active cart to checkout."
    default_code = "NO_ACTIVE_CART"


class CartEmptyException(ValidationException):
    default_detail = "Cart is empty."
    default_code = "CART_EMPTY"


class CheckoutFailedException(ConflictException):
    default_detail = "Checkout failed. Please retry."
    default_code = "CHECKOUT_FAILED"
