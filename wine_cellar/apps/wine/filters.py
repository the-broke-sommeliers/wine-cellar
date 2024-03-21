import django_filters

from wine_cellar.apps.wine.forms import WineFilterForm
from wine_cellar.apps.wine.models import Wine


class WineFilter(django_filters.FilterSet):
    class Meta:
        form = WineFilterForm
        model = Wine
        fields = [
            "name",
            "wine_type",
            "elaborate",
            "grapes",
            "classification",
            "food_pairings",
            "body",
            "acidity",
            "abv",
            "capacity",
            "vintage",
            "region",
            "winery",
        ]
