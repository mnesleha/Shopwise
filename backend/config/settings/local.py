import os
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.1.106"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}


INTERNAL_IPS = [
    "127.0.0.1",
]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "127.0.0.1")  # Mailpit runs locally
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

# Relaxed rate limits for local development — avoids hitting the throttle
# during manual testing while keeping the production-identical code path active.
PW_RESET_REQUEST_RL_PER_IP = 1000
PW_RESET_CONFIRM_RL_PER_IP = 1000
