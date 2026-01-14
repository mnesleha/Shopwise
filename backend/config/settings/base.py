import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = "unsafe-placeholder-key"

DEBUG = False

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework_simplejwt.token_blacklist",
    "accounts",
    "categories",
    "products",
    "discounts",
    "orders",
    "orderitems",
    "payments",
    "carts",
    "utils",
    'django_filters',
    "rest_framework",
    'drf_spectacular',
    'drf_spectacular_sidecar',
    "debug_toolbar"
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

RESERVATION_TTL_GUEST_SECONDS = int(
    os.getenv("RESERVATION_TTL_GUEST_SECONDS", 15 * 60))
RESERVATION_TTL_AUTH_SECONDS = int(
    os.getenv("RESERVATION_TTL_AUTH_SECONDS", 2 * 60 * 60))

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.exceptions.handler.custom_exception_handler",
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Shopwise API',
    'DESCRIPTION': """
## What is Shopwise

Shopwise is a quality-driven showcase project.

## Why it exists

This API demonstrates:
- QA as equal development partner
- documentation as a quality tool
- testing as part of design

## Quality Strategy

- Test Driven Development
- Documentation Driven Development
- OpenAPI as single source of truth

## Intended Audience

- Recruiters
- Test Managers
- Project Managers

## Pricing Rules

This API follows strict and deterministic pricing rules to ensure
consistency between cart preview and checkout.

### Base Price
- `base_price = unit_price × quantity`

### Discount Application
- At most **one discount** can be applied per product.
- Discount precedence:
  1. **FIXED** discount
  2. **PERCENT** discount
- Discounts never reduce price below **0.00**.

### Rounding
- Prices are rounded to **2 decimal places**
- Rounding mode: **ROUND_HALF_UP**

### Price Snapshotting
- Product price is snapshotted at **add-to-cart time**
- Checkout uses `price_at_add_time`
- Later product price changes do **not** affect existing carts
""",
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
        'displayRequestDuration': True,
    },
    'TAGS': [
        {'name': 'Users', 'description': 'User management'},
        {'name': 'Auth', 'description': 'Authentication & authorization'},
        {'name': 'Products', 'description': 'Product catalog management'},
        {'name': 'Categories', 'description': 'Product category management'},
        {'name': 'Orders', 'description': 'Read-only order resources'},
        {'name': 'Payments', 'description': 'Payment simulation and processing'},
        {'name': 'Discounts', 'description': 'Discount and promotion management'},
        {
            'name': 'Cart',
            'description': (
                'User shopping cart representing intent. '
                'A user can have at most one ACTIVE cart.'
            ),
        },
        {
            'name': 'Cart Items',
            'description': (
                'Items added to the active cart. '
                'Price is snapshotted at add time.'
            ),
        },
        {
            'name': 'Cart Checkout',
            'description': (
                'Cart checkout workflow. '
                'Converts cart into an order.'
            ),
        },
    ],
}
