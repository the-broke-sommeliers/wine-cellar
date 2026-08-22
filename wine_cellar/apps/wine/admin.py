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
    # A wine must always keep at least one vintage - VintageDeleteView
    # enforces this in the app views, mirror it here so the admin can't
    # delete the inline down to zero.
    min_num = 1
    validate_min = True
    fields = [
        "year",
        "abv",
        "barcode",
        "price",
        "drink_by",
        "rating",
        "comment",
        "user",
    ]
    # Always matches the parent wine's user - not meant to be reassigned
    # independently from the admin.
    readonly_fields = ["user"]


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


@admin.register(Vintage)
class VintageAdmin(admin.ModelAdmin):
    list_display = ["wine", "year", "barcode", "user"]
    search_fields = ["wine__name", "barcode"]
    fields = [
        "wine",
        "year",
        "abv",
        "barcode",
        "price",
        "drink_by",
        "rating",
        "comment",
        "user",
    ]


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
