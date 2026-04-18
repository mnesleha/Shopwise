import os
from .base import *

DEBUG = False
ENABLE_DEBUG_TOOLBAR = os.getenv("ENABLE_DEBUG_TOOLBAR", "false").lower() == "true"
configure_debug_toolbar()

ALLOWED_HOSTS = [
    os.getenv("RENDER_EXTERNAL_HOSTNAME", ""),
    "localhost",
]

# remove empty values
ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]

CSRF_TRUSTED_ORIGINS = [
    os.getenv("FRONTEND_BASE_URL", ""),
    os.getenv("PUBLIC_BASE_URL", ""),
]
CSRF_TRUSTED_ORIGINS = [u for u in CSRF_TRUSTED_ORIGINS if u]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

SERVE_MEDIA = os.getenv("SERVE_MEDIA", "true").lower() == "true"

# cookies for HTTPS deploy
AUTH_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CORS_ALLOWED_ORIGINS = [
    os.getenv("FRONTEND_BASE_URL", ""),
]
CORS_ALLOWED_ORIGINS = [u for u in CORS_ALLOWED_ORIGINS if u]

# Cloudflare R2 media storage via django-storages / S3 backend

AWS_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
AWS_STORAGE_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
AWS_S3_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
AWS_S3_REGION_NAME = os.getenv("R2_REGION", "auto")

# R2 / S3 compatibility
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_ADDRESSING_STYLE = "virtual"
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

# Optional but useful
AWS_S3_FILE_OVERWRITE = False

# Public base URL for generated media links
AWS_MEDIA_CUSTOM_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN", "")

if AWS_MEDIA_CUSTOM_DOMAIN:
    MEDIA_URL = f"https://{AWS_MEDIA_CUSTOM_DOMAIN}/"
else:
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"

STORAGES["default"] = {
    "BACKEND": "storages.backends.s3.S3Storage",
    "OPTIONS": {
        "access_key": AWS_ACCESS_KEY_ID,
        "secret_key": AWS_SECRET_ACCESS_KEY,
        "bucket_name": AWS_STORAGE_BUCKET_NAME,
        "endpoint_url": AWS_S3_ENDPOINT_URL,
        "region_name": AWS_S3_REGION_NAME,
        "default_acl": None,
        "querystring_auth": False,
        "file_overwrite": False,
        "custom_domain": AWS_MEDIA_CUSTOM_DOMAIN or None,
    },
}

Q_CLUSTER["workers"] = int(os.getenv("Q_CLUSTER_WORKERS", "1"))
Q_CLUSTER["queue_limit"] = int(os.getenv("Q_CLUSTER_QUEUE_LIMIT", "20"))
Q_CLUSTER["timeout"] = int(os.getenv("Q_CLUSTER_TIMEOUT", "120"))
Q_CLUSTER["retry"] = int(os.getenv("Q_CLUSTER_RETRY", "150"))

EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "70"))

ACQUIREMOCK_BASE_URL = os.getenv("ACQUIREMOCK_BASE_URL", "")
ACQUIREMOCK_API_KEY = os.getenv("ACQUIREMOCK_API_KEY", "")
ACQUIREMOCK_WEBHOOK_SECRET = os.getenv("ACQUIREMOCK_WEBHOOK_SECRET", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "carts": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "payments": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "suppliers": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}