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
# Prod recommendation is noted next to each constant.

# POST /auth/register/
REGISTER_RL_PER_IP = 1000           # prod: 5 / 60 s per IP
REGISTER_RL_WINDOW_S = 60

# POST /auth/login/
LOGIN_RL_PER_IP = 1000              # prod: 10 / 60 s per IP
LOGIN_RL_WINDOW_S = 60
LOGIN_RL_PER_EMAIL = 1000           # prod: 5 / 600 s per email
LOGIN_RL_PER_EMAIL_WINDOW_S = 600

# POST /auth/refresh/
REFRESH_RL_PER_IP = 1000            # prod: 30 / 60 s per IP
REFRESH_RL_WINDOW_S = 60

# POST /auth/logout/
LOGOUT_RL_PER_IP = 1000             # prod: 30 / 60 s per IP
LOGOUT_RL_WINDOW_S = 60

# POST /auth/password-reset/request/
PW_RESET_REQUEST_RL_PER_IP = 1000   # prod: 10 / 3600 s per IP
PW_RESET_REQUEST_RL_WINDOW_S = 3600

# POST /auth/password-reset/confirm/
PW_RESET_CONFIRM_RL_PER_IP = 1000   # prod: 20 / 3600 s per IP
PW_RESET_CONFIRM_RL_WINDOW_S = 3600

# GET /api/v1/account/confirm-email-change/
CONFIRM_EMAIL_CHANGE_RL_PER_IP = 1000   # prod: 30 / 60 s per IP
CONFIRM_EMAIL_CHANGE_RL_WINDOW_S = 60

# GET /api/v1/account/cancel-email-change/
CANCEL_EMAIL_CHANGE_RL_PER_IP = 1000    # prod: 30 / 60 s per IP
CANCEL_EMAIL_CHANGE_RL_WINDOW_S = 60

# POST /api/v1/account/logout-all/
LOGOUT_ALL_RL_PER_USER = 1000       # prod: 10 / 60 s per user
LOGOUT_ALL_RL_WINDOW_S = 60

# POST /api/v1/account/change-password/
CHANGE_PASSWORD_RL_PER_USER = 1000  # prod: 5 / 600 s per user
CHANGE_PASSWORD_RL_PER_IP = 1000    # prod: 10 / 600 s per IP
CHANGE_PASSWORD_RL_WINDOW_S = 600
