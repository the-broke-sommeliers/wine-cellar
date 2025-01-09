from django.contrib import admin

from wine_cellar.apps.wine.models import Wine


@admin.register(Wine)
class WineAdmin(admin.ModelAdmin):
    list_display = ["name", "barcode"]
    fields = ["name", "barcode"]