from .base import *

DEBUG = True

# Keep test settings self-contained and deterministic.
# These values are NOT used in production and are safe for local test runs.
SECRET_KEY = "test-secret-key"
GUEST_ACCESS_TOKEN_PEPPER = "test-pepper"
PUBLIC_BASE_URL = "http://127.0.0.1:8000"

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
