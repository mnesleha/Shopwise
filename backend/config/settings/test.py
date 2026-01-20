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

Q_CLUSTER = {
    "name": "shopwise-test",
    "orm": "default",
    "sync": True,
    "workers": 1,
    "timeout": 10,
    "retry": 20,
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "127.0.0.1")  # Mailpit runs locally
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
