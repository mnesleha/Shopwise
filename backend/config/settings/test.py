from .base import *

DEBUG = True

# Keep test settings self-contained and deterministic.
# These values are NOT used in production and are safe for local test runs.
SECRET_KEY = "test-secret-key"
GUEST_ACCESS_TOKEN_PEPPER = "test-pepper"
# PUBLIC_BASE_URL = "http://127.0.0.1:8000"
PUBLIC_BASE_URL = "http://192.168.1.106:8000"
# Frontend base URL used in password-reset emails during tests.
FRONTEND_BASE_URL = "http://localhost:3000"
FRONTEND_RETURN_URL = "http://localhost:3000/checkout/payment/return"

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "192.168.1.106"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Prevent VersatileImageField from physically creating resized images during
# tests. URLs are still generated correctly; only on-disk processing is skipped.
VERSATILEIMAGEFIELD_SETTINGS = {
    "create_images_on_demand": False,
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

# Store raw email-change tokens in debug DB columns so test helpers can
# retrieve them without intercepting outbound email (ADR-035).
STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS = True

# Explicitly disable rate limiting in tests so throttle counters never block
# test requests.  Intentionally a separate flag from STORE_CHANGE_EMAIL_TOKENS_FOR_TESTS
# so each setting has one clear responsibility.
DISABLE_RATE_LIMITING_FOR_TESTS = True

# Rate-limit constants — high values as a belt-and-suspenders safety net in
# case the DISABLE_RATE_LIMITING_FOR_TESTS bypass is ever missed in a new view.
REGISTER_RL_PER_IP = 10000
REGISTER_RL_WINDOW_S = 60
LOGIN_RL_PER_IP = 10000
LOGIN_RL_WINDOW_S = 60
LOGIN_RL_PER_EMAIL = 10000
LOGIN_RL_PER_EMAIL_WINDOW_S = 600
REFRESH_RL_PER_IP = 10000
REFRESH_RL_WINDOW_S = 60
LOGOUT_RL_PER_IP = 10000
LOGOUT_RL_WINDOW_S = 60
PW_RESET_REQUEST_RL_PER_IP = 10000
PW_RESET_REQUEST_RL_WINDOW_S = 3600
PW_RESET_CONFIRM_RL_PER_IP = 10000
PW_RESET_CONFIRM_RL_WINDOW_S = 3600
CONFIRM_EMAIL_CHANGE_RL_PER_IP = 10000
CONFIRM_EMAIL_CHANGE_RL_WINDOW_S = 60
CANCEL_EMAIL_CHANGE_RL_PER_IP = 10000
CANCEL_EMAIL_CHANGE_RL_WINDOW_S = 60
LOGOUT_ALL_RL_PER_USER = 10000
LOGOUT_ALL_RL_WINDOW_S = 60
CHANGE_PASSWORD_RL_PER_USER = 10000
CHANGE_PASSWORD_RL_PER_IP = 10000
CHANGE_PASSWORD_RL_WINDOW_S = 600
BOOTSTRAP_RL_PER_IP = 10000
BOOTSTRAP_RL_WINDOW_S = 60
BOOTSTRAP_RL_PER_TOKEN = 10000
BOOTSTRAP_RL_TOKEN_WINDOW_S = 60

# Deterministic refresh TTLs for remember-me tests.
# Values are intentionally short (seconds, not days) to keep test assertions fast,
# but remember value is strictly larger than standard to validate the feature.
AUTH_REFRESH_TTL_SECONDS = 3600          # 1 hour (standard, test)
AUTH_REFRESH_TTL_REMEMBER_SECONDS = 7200  # 2 hours (remember-me, test)
