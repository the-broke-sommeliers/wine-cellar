import os

import sentry_sdk

from wine_cellar.__init__ import __version__
from wine_cellar.conf.prod import *  # noqa: F403

DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
WEBPACK_LOADER["DEFAULT"]["CACHE"] = not DEBUG  # noqa: F405
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS").split(" ")
SECRET_KEY = os.environ.get("SECRET_KEY")
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("SQL_DATABASE", BASE_DIR / "db.sqlite3"),  # noqa: F405
        "USER": os.environ.get("SQL_USER", "user"),
        "PASSWORD": os.environ.get("SQL_PASSWORD", "password"),
        "HOST": os.environ.get("SQL_HOST", "localhost"),
        "PORT": os.environ.get("SQL_PORT", "5432"),
    }
}

CSRF_TRUSTED_ORIGINS = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS").split(" ")

CSP_FORM_ACTION_EXTRA = os.environ.get("DJANGO_CSP_FORM_ACTION_EXTRA", "")
if CSP_FORM_ACTION_EXTRA:
    SECURE_CSP["form-action"] += CSP_FORM_ACTION_EXTRA.split(" ")  # noqa: F405

MEDIA_ROOT = "mediafiles"
STATIC_ROOT = "staticfiles"

SITE_URL = os.environ.get("DJANGO_SITE_URL")

ENABLE_SIGNUPS = os.environ.get("DJANGO_ENABLE_SIGNUPS", "False") == "True"
ACCOUNT_EMAIL_VERIFICATION = "mandatory" if ENABLE_SIGNUPS else "optional"
ACCOUNT_SIGNUP_FIELDS = (
    ["email*", "username*", "password1*", "password2*"]
    if ENABLE_SIGNUPS
    else ["email", "username*", "password1*", "password2*"]
)


EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST")
EMAIL_PORT = os.environ.get("DJANGO_EMAIL_PORT")
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_USER")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_PASSWORD")
# USE_TLS and USE_SSL are mutual exclusive
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.environ.get("DJANGO_EMAIL_USE_SSL", "False") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL")

MAILERS = {
    "default": {
        "BACKEND": (
            "django.core.mail.backends.smtp.EmailBackend"
            if EMAIL_HOST
            else "django.core.mail.backends.console.EmailBackend"
        ),
        "OPTIONS": {
            "host": EMAIL_HOST,
            "port": int(EMAIL_PORT) if EMAIL_PORT else None,
            "username": EMAIL_HOST_USER,
            "password": EMAIL_HOST_PASSWORD,
            "use_tls": EMAIL_USE_TLS,
            "use_ssl": EMAIL_USE_SSL,
        },
    },
}

CELERY_BROKER_URL = os.environ.get(
    "REDIS_URL",
    "redis://redis:6379",
)
CELERY_RESULT_BACKEND = os.environ.get(
    "REDIS_URL",
    "redis://redis:6379",
)

# Use a separate logical DB (index 1) from Celery's broker/backend (index 0)
# to keep key namespaces apart on the same Redis instance.
CACHES["wine_prefill"] = {  # noqa: F405
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": f"{os.environ.get('REDIS_URL', 'redis://redis:6379')}/1",
}

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        release="wine-cellar@" + __version__,
        send_default_pii=True,
        max_request_body_size="always",
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
    )

AI_MODEL = os.environ.get("AI_MODEL", "")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
