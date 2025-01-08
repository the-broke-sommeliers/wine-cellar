import django_filters
from django.db.models import Q

from wine_cellar.apps.wine.forms import WineFilterForm
from wine_cellar.apps.wine.models import Wine


class WineFilter(django_filters.FilterSet):
    class Meta:
        form = WineFilterForm
        model = Wine
        fields = [
            "name",
            "wine_type",
            "category",
            "vintage",
            "vineyard",
            "grapes",
            "food_pairings",
            "source",
            "country",
        ]

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        user_filters = ["vineyard", "grapes", "food_pairings", "source"]
        for user_filter in user_filters:
            self.filters[user_filter].queryset = self.filters[
                user_filter
            ].queryset.filter(Q(user=None) | Q(user=request.user))
