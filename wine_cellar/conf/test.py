import os

from .settings import *  # noqa: F403

MEDIA_ROOT = BASE_DIR / "test_media/"  # noqa: F405

CELERY_TASK_ALWAYS_EAGER = True

# A freshly created test user has never "seen" a What's New release, so the
# full-viewport overlay (base.html) would render - and intercept clicks - on
# every page in every test. Off by default here; tests that specifically
# exercise the What's New feature (tests/user/test_whats_new.py) opt back in.
ENABLE_WHATS_NEW = os.environ.get("DJANGO_ENABLE_WHATS_NEW", "False") == "True"

STATIC_ROOT = BASE_DIR / "static"  # noqa: F405

SQL_ENGINE = os.environ.get("SQL_ENGINE", "django.db.backends.sqlite3")
DATABASES = {
    "default": {
        "ENGINE": SQL_ENGINE,
        "NAME": os.environ.get("SQL_DATABASE", "db.sqlite3"),
        "USER": os.environ.get("SQL_USER", "user"),
        "PASSWORD": os.environ.get("SQL_PASSWORD", "password"),
        "HOST": os.environ.get("SQL_HOST", "localhost"),
        "PORT": os.environ.get("SQL_PORT", "5432"),
    }
}
if SQL_ENGINE == "django.db.backends.sqlite3":
    DATABASES["default"]["TEST"] = {"NAME": "test_db.sqlite3"}
