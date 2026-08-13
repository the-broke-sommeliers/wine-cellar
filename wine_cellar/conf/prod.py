from wine_cellar.conf.settings import *  # noqa: F403, F401

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
