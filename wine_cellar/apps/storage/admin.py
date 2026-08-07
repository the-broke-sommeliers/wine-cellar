from django.contrib import admin

from wine_cellar.apps.storage.models import Storage, StorageItem, StorageLabel


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location", "created")
    search_fields = ("name", "location")
    list_filter = ("created",)


@admin.register(StorageItem)
class StorageItemAdmin(admin.ModelAdmin):
    list_display = ("id", "storage", "wine", "row", "column", "created")
    search_fields = ("wine__name", "storage__name")
    list_filter = ("storage",)


@admin.register(StorageLabel)
class StorageLabelAdmin(admin.ModelAdmin):
    list_display = ("id", "storage", "axis", "index", "name")
    search_fields = ("name", "storage__name")
    list_filter = ("storage", "axis")
