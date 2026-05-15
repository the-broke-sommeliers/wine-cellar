import django_filters
from django.db.models import F, Q
from django.db.models.expressions import OrderBy
from django.utils.translation import gettext_lazy as _
from django_filters import ChoiceFilter, OrderingFilter

from wine_cellar.apps.wine.forms import WineFilterForm
from wine_cellar.apps.wine.models import Wine


class NullsLastOrderingFilter(OrderingFilter):
    def filter(self, qs, value):
        if not value:
            return qs

        ordering = []
        for param in value:
            descending = param.startswith("-")
            field_name = param.lstrip("-")

            ordering.append(
                OrderBy(
                    F(field_name),
                    descending=descending,
                    nulls_last=True,
                )
            )

        return qs.order_by(*ordering)


class WineFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        label=_("Name contains"), field_name="name", lookup_expr="icontains"
    )
    stock = ChoiceFilter(
        method="filter_stock",
        label=_("Show only in stock"),
        choices=((0, _("No")), (1, _("Yes"))),
        empty_label=None,
        null_label=None,
    )
    order = NullsLastOrderingFilter(
        choices=(
            ("-created", _("Recently Added")),
            ("created", _("Least Recently Added")),
            ("-name", _("Name Descending")),
            ("name", _("Name Ascending")),
            ("-vintage", _("Youngest First")),
            ("vintage", _("Oldest First")),
            ("drink_by", _("Drink By")),
            ("-effective_price", _("Highest Price (Avg)")),
            ("effective_price", _("Lowest Price (Avg)")),
        ),
        label=_("Sorting"),
        empty_label=None,
        null_label=None,
    )

    def filter_stock(self, queryset, name, value):
        if value == "1":
            return queryset.filter(
                storageitem__isnull=False, storageitem__deleted=False
            ).distinct()
        else:
            return queryset

    class Meta:
        form = WineFilterForm
        model = Wine
        fields = [
            "name",
            "wine_type",
            "attributes",
            "category",
            "vintage",
            "vineyard",
            "grapes",
            "food_pairings",
            "source",
            "country",
            "stock",
        ]
        labels = {
            "name": _("Name Contains"),
            "wine_type": _("Wine Type"),
            "attributes": _("Attributes"),
            "category": _("Category"),
            "vintage": _("Vintage"),
            "vineyard": _("Vineyard"),
            "grapes": _("Grapes"),
            "food_pairings": _("Food Pairings"),
            "source": _("Source"),
            "country": _("Country"),
        }

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        user_filters = [
            "vineyard",
            "grapes",
            "food_pairings",
            "source",
            "attributes",
        ]
        for user_filter in user_filters:
            self.filters[user_filter].queryset = self.filters[
                user_filter
            ].queryset.filter(Q(user=None) | Q(user=request.user))

        for key, fil in self.filters.items():
            if key in self.Meta.labels:
                fil.label = self.Meta.labels[key]
