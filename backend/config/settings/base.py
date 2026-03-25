from sentry_sdk.integrations.django import DjangoIntegration
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-placeholder-key")

# Guest token hashing pepper (capability token hashing).
# Keep it in env for dev/prod; tests override it in config.settings.test.
GUEST_ACCESS_TOKEN_PEPPER = os.getenv("GUEST_ACCESS_TOKEN_PEPPER", "")

DEBUG = True

APPEND_SLASH = False  # Pure API backend — trailing slash handled by clients

ALLOWED_HOSTS = []

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
# Frontend base URL — used to build links in emails that must point to the
# Next.js frontend (e.g. password-reset flow) rather than the API server.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'corsheaders',
    "rest_framework_simplejwt.token_blacklist",
    "rest_framework",
    "django_q",
    "martor",
    "versatileimagefield",
    "storages",
    "accounts",
    "categories",
    "products",
    "discounts",
    "orders",
    "orderitems",
    "payments",
    "auditlog",
    "carts",
    "notifications",
    "suppliers",
    "utils",
    'django_filters',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'django_prices',
    "debug_toolbar",
    "django_countries",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [BASE_DIR / 'templates'],
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

Q_CLUSTER = {
    "name": "shopwise",
    "orm": "default",
    "workers": 4,
    "timeout": 60,
    "retry": 120,
    "queue_limit": 50,
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.106:3000",  # local network access for mobile testing
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrf-token",
    "x-requested-with",
    "sentry-trace",
    "baggage",
]

SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True

AUTH_COOKIE_ACCESS = "access_token"
AUTH_COOKIE_REFRESH = "refresh_token"
AUTH_COOKIE_SECURE = not DEBUG
AUTH_COOKIE_SAMESITE = "Lax"   # pro Next rewrites ideální
AUTH_COOKIE_PATH = "/"

def auth_cookie_kwargs():
    return dict(
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        path=AUTH_COOKIE_PATH,
    )


# Sentry - can be disabled via SENTRY_ENABLED=false
SENTRY_ENABLED = os.getenv("SENTRY_ENABLED", "true").lower() == "true"

sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.WARNING
)

if SENTRY_ENABLED:
    sentry_sdk.init(
        dsn="https://2becc686d197008cfe9d5b4bd58b42f7@o4510765395476480.ingest.de.sentry.io/4510765407862864",
        integrations=[
            DjangoIntegration(),
            sentry_logging,
        ],
        traces_sample_rate=0.1,
        environment="development",
        send_default_pii=True,
    )

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Shopwise <no-reply@shopwise.local>")

RESERVATION_TTL_GUEST_SECONDS = int(
    os.getenv("RESERVATION_TTL_GUEST_SECONDS", 15 * 60))
RESERVATION_TTL_AUTH_SECONDS = int(
    os.getenv("RESERVATION_TTL_AUTH_SECONDS", 2 * 60 * 60))

STATIC_URL = "static/"

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Django 4.2+ unified storage configuration.
# Swap "default" backend to a cloud storage (e.g. django-storages S3Backend)
# via environment-specific settings without touching application code.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Martor — markdown editor used for product descriptions.
# Images uploaded through the editor are stored under MARTOR_UPLOAD_PATH,
# isolated from the future product gallery uploads.
# ---------------------------------------------------------------------------
MARTOR_UPLOAD_URL = "/api/v1/descriptions/upload/"
MARTOR_UPLOAD_PATH = "products/descriptions"

# Disable external image hosting; all uploads go through our own endpoint.
MARTOR_ENABLE_CONFIGS = {
    "emoji": "true",
    "imgur": "true",
    "mention": "false",
    "guardian": "true",
    "living": "false",
    "spellcheck": "false",
    "hljs": "true",
    "jquery": "true",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.exceptions.handler.custom_exception_handler",
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

# Refresh token TTLs — read at runtime by LoginView so test/local overrides apply.
# Standard session (no "remember me"): 7 days.
# Long-lived session ("remember me" checked): 30 days.
AUTH_REFRESH_TTL_SECONDS: int = 7 * 24 * 3600        # 7 days
AUTH_REFRESH_TTL_REMEMBER_SECONDS: int = 30 * 24 * 3600  # 30 days

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(seconds=AUTH_REFRESH_TTL_SECONDS),
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

# Safety guard: rate limiting must always be active in production.
# Set to True only in test.py — never in production or local settings.
DISABLE_RATE_LIMITING_FOR_TESTS = False

# ---------------------------------------------------------------------------
# Catalogue / stock settings
# ---------------------------------------------------------------------------

# Products with stock_quantity <= LOW_STOCK_THRESHOLD are shown as LOW_STOCK.
# Override in local.py or per-environment as needed.
LOW_STOCK_THRESHOLD = 5

# ---------------------------------------------------------------------------
# Overdue inventory reservation expiration settings
# ---------------------------------------------------------------------------

# Cron expression controlling when the overdue reservation expiration job runs.
# Default: every 15 minutes — reservations have short TTLs (guest: 15 min,
# auth: 2 h), so a frequent sweep keeps cancelled orders fresh.
OVERDUE_RESERVATIONS_CLEANUP_CRON: str = os.getenv(
    "OVERDUE_RESERVATIONS_CLEANUP_CRON", "*/15 * * * *"
)

# ---------------------------------------------------------------------------
# Anonymous cart cleanup settings
# ---------------------------------------------------------------------------

# Number of days after which an anonymous cart is considered expired.
# Used by both the management command and the scheduled django-q2 job.
ANONYMOUS_CART_TTL_DAYS: int = int(os.getenv("ANONYMOUS_CART_TTL_DAYS", 7))

# Cron expression controlling when the cleanup job runs.
# Default: 03:00 UTC every day.
ANONYMOUS_CART_CLEANUP_CRON: str = os.getenv(
    "ANONYMOUS_CART_CLEANUP_CRON", "0 3 * * *"
)

# ---------------------------------------------------------------------------
# Checkout price-change detection settings
# ---------------------------------------------------------------------------
# These thresholds drive per-line severity classification when the current
# effective price at checkout differs from price_at_add_time.
#
# INFO    — noticeable but minor change; surfaced to the customer for awareness.
# WARNING — significant change; the customer should be clearly informed.
#
# Values are percentages (e.g. 1 means 1 %).
# WARNING threshold must be >= INFO threshold; the service enforces this.

CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT: int = int(
    os.getenv("CHECKOUT_PRICE_CHANGE_INFO_THRESHOLD_PERCENT", 10) # 1
)
CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT: int = int(
    os.getenv("CHECKOUT_PRICE_CHANGE_WARNING_THRESHOLD_PERCENT", 50) # 5
)

# ---------------------------------------------------------------------------
# AcquireMock payment gateway settings
# ---------------------------------------------------------------------------
# AcquireMock is a hosted mock payment gateway used during development and
# architecture preparation for real card PSP integration.
#
# ACQUIREMOCK_BASE_URL  — base URL of the AcquireMock server (no trailing slash).
# ACQUIREMOCK_API_KEY   — authentication token sent as X-Api-Key header.
# ACQUIREMOCK_TIMEOUT   — HTTP request timeout in seconds (default: 10).
#
# These values must be set in the environment (or local.py) before CARD
# payment can be started.  The provider will fail explicitly when the URL
# or key is empty.
ACQUIREMOCK_BASE_URL: str = os.getenv("ACQUIREMOCK_BASE_URL", "")
ACQUIREMOCK_API_KEY: str = os.getenv("ACQUIREMOCK_API_KEY", "")
ACQUIREMOCK_TIMEOUT: int = int(os.getenv("ACQUIREMOCK_TIMEOUT", 10))
# Shared secret used to verify HMAC-SHA256 webhook signatures from AcquireMock.
# Must match the secret configured in the AcquireMock dashboard/environment.
ACQUIREMOCK_WEBHOOK_SECRET: str = os.getenv("ACQUIREMOCK_WEBHOOK_SECRET", "")
