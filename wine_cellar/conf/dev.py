from wine_cellar.conf.settings import *  # noqa: F403, F401

try:
    import debug_toolbar  # noqa: F401
except ImportError:
    pass
else:
    INSTALLED_APPS += ("debug_toolbar",)  # noqa: F405
    MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)  # noqa: F405
    INTERNAL_IPS = ("127.0.0.1", "localhost")
