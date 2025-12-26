from pathlib import Path

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
    "categories",
    "products",
    "discounts",
    "orders",
    "orderitems",
    "payments",
    "carts",
    "rest_framework",
    'drf_spectacular',
    'drf_spectacular_sidecar',
    "debug_toolbar"
]

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

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
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
            'name': 'Checkout',
            'description': (
                'Cart checkout workflow. '
                'Converts cart into an order.'
            ),
        },
    ],
}
