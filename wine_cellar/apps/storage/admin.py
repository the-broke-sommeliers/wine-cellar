from django.contrib import admin

from wine_cellar.apps.storage.models import (
    Storage,
    StorageItem,
    StorageItemEvent,
    StorageLabel,
)


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location", "created")
    search_fields = ("name", "location")
    list_filter = ("created",)


@admin.register(StorageItem)
class StorageItemAdmin(admin.ModelAdmin):
    list_display = ("id", "storage", "vintage", "row", "column", "created")
    search_fields = ("vintage__wine__name", "storage__name")
    list_filter = ("storage",)


@admin.register(StorageItemEvent)
class StorageItemEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "wine_name",
        "vintage_year",
        "storage_item",
        "event_type",
        "created",
    )
    search_fields = ("wine_name", "storage_item__storage__name")
    list_filter = ("event_type", "created")


@admin.register(StorageLabel)
class StorageLabelAdmin(admin.ModelAdmin):
    list_display = ("id", "storage", "axis", "index", "name")
    search_fields = ("name", "storage__name")
    list_filter = ("storage", "axis")
