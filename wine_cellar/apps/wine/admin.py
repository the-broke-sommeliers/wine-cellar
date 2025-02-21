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
    list_display = ["name", "barcode"]
    fields = ["name", "barcode"]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["name"]
    fields = ["name"]


@admin.register(Grape)
class GrapeAdmin(admin.ModelAdmin):
    list_display = ["name"]
    fields = ["name"]


@admin.register(Vineyard)
class VineyardAdmin(admin.ModelAdmin):
    list_display = ["name", "country"]
    fields = ["name", "website", "country", "region"]


@admin.register(FoodPairing)
class FoodPairingAdmin(admin.ModelAdmin):
    list_display = ["name"]
    fields = ["name"]


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["name"]
    fields = ["name"]
