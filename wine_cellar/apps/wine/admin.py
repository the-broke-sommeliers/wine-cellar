from django.contrib import admin

from wine_cellar.apps.wine.models import Classification


@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    pass
