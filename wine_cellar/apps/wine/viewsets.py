from django_filters import rest_framework as django_filters
from rest_framework import filters, viewsets

from wine_cellar.apps.wine.models import Wine
from wine_cellar.apps.wine.serializers import WineSerializer


class WineViewSet(viewsets.ModelViewSet):
    queryset = (
        Wine.objects.all().select_related("region", "winery").prefetch_related("grapes")
    )
    serializer_class = WineSerializer
    filter_backends = [filters.SearchFilter, django_filters.DjangoFilterBackend]
    filterset_fields = [
        "wine_type",
        "grapes",
        "vintage",
        "winery",
        "food_pairings",
        "capacity",
        "region",
        "classification",
        "elaborate",
    ]
    search_fields = [
        "name",
        "grapes__name",
        "winery__name",
    ]
