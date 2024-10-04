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
            # "elaborate",
            "category",
            # "classification",
            # "body",
            # "acidity",
            # "abv",
            # "capacity",
            "vintage",
            "region",
            "winery",
            "grapes",
            "food_pairings",
            "source",
        ]
