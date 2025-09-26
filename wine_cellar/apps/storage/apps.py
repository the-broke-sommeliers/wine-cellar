from django.apps import AppConfig


class StorageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wine_cellar.apps.storage"

    def ready(self):
        import wine_cellar.apps.storage.signals  # noqa: F401
