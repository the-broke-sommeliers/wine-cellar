from django.contrib import admin

from wine_cellar.apps.wine.models import (
    Attribute,
    FoodPairing,
    Grape,
    Size,
    Source,
    Vineyard,
    Vintage,
    Wine,
)


class VintageInline(admin.TabularInline):
    model = Vintage
    extra = 0
    fields = [
        "year", "abv", "barcode", "price", "drink_by", "rating", "comment", "user"
    ]


@admin.register(Wine)
class WineAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    fields = [
        "name",
        "user",
        "location",
        "region",
        "appellation",
        "vineyard",
        "source",
        "grapes",
        "attributes",
    ]
    inlines = [VintageInline]


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


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    fields = ["name", "user"]
