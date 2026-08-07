from wine_cellar.conf.settings import *  # noqa: F403, F401

# Plain `make server` runs no Celery worker/broker (those only exist under
# Docker Compose - see docker_settings.py/docker_dev_settings.py), so the
# AI wine-upload task would otherwise hang trying to reach a nonexistent
# broker. Run it inline instead, same as test.py does.
CELERY_TASK_ALWAYS_EAGER = True

try:
    import debug_toolbar  # noqa: F401
except ImportError:
    pass
else:
    INSTALLED_APPS += ("debug_toolbar",)  # noqa: F405
    MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)  # noqa: F405
    INTERNAL_IPS = ("127.0.0.1", "localhost")

try:
    from .local import *  # noqa: F403, F401
except ImportError:
    pass
