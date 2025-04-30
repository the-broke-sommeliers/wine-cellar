from django.contrib import admin

from wine_cellar.apps.wine.models import (
    FoodPairing,
    Grape,
    Size,
    Source,
    Vineyard,
    Wine,
)


@admin.register(Wine)
class WineAdmin(admin.ModelAdmin):
    list_display = ["name", "barcode", "user"]
    fields = ["name", "barcode", "user"]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    fields = ["name", "user"]


@admin.register(Grape)
class GrapeAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    fields = ["name", "user"]


@admin.register(Vineyard)
class VineyardAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "user"]
    fields = ["name", "website", "country", "region", "user"]


@admin.register(FoodPairing)
class FoodPairingAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    fields = ["name", "user"]


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    fields = ["name", "user"]
