import json
from datetime import datetime

import pycountry
from django import forms
from django.core import validators
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Q
from django.forms import ImageField
from django.utils.translation import gettext as _

from wine_cellar.apps.wine.fields import OpenMultipleChoiceField
from wine_cellar.apps.wine.models import (
    Category,
    Classification,
    FoodPairing,
    Grape,
    Size,
    Source,
    Vineyard,
    WineType,
)


class TomSelectMixin:
    def set_tom_config(
        self,
        name,
        create=False,
        items=[],
        max_items=None,
        max_options=50,
        clear=True,
        placeholder=None,
        closeAfterSelect=True,
    ):
        tom_config = {
            "create": create,
            "maxItems": max_items,
            "closeAfterSelect": closeAfterSelect,
        }
        if items:
            tom_config["items"] = items
        if max_options:
            tom_config["maxOptions"] = None if max_options == -1 else max_options
        if placeholder is not None:
            tom_config["placeholder"] = placeholder

        self.fields[name].widget.attrs.update(
            {
                "data-tom_config": json.dumps(tom_config),
                "data-clear": "true" if clear else "false",
            }
        )


class WineBaseForm(TomSelectMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        user_fields = [
            "vineyard",
            "classification",
            "grapes",
            "food_pairings",
            "source",
            "size",
        ]
        for user_field in user_fields:
            self.fields[user_field].queryset = self.fields[
                user_field
            ].queryset.model.objects.filter(Q(user=None) | Q(user=user))
            self.fields[user_field].user = user

    class Meta:
        abstract = True

    name = forms.CharField(
        max_length=100,
        help_text=_("Enter the name of the wine as indicated on the label."),
    )
    wine_type = forms.CharField(
        max_length=2,
        widget=forms.Select(choices=WineType),
        help_text=_("Select the type of wine from the dropdown."),
    )
    category = forms.CharField(
        label="Sweetness",
        required=False,
        max_length=2,
        widget=forms.Select(choices=Category),
        help_text=_("Select the sweetness level of the wine."),
    )
    country = forms.CharField(
        max_length=250,
        widget=forms.Select(
            choices={country.alpha_2: country.name for country in pycountry.countries},
        ),
        help_text=_(
            "Select the country the wine was produced in as indicated on the " "label."
        ),
    )
    size = OpenMultipleChoiceField(
        queryset=Size.objects.none(),
        field_name="name",
        label="Size",
        help_text=_(
            "Please enter the volume of bottle or box ect. in liters, e.g. 0.75."
        ),
    )
    abv = forms.FloatField(
        required=False,
        validators=[
            validators.MinValueValidator(0.0),
            validators.MaxValueValidator(100.0),
        ],
        help_text=_(
            "Please enter the percentage of alcohol in the"
            " wine. This information is typically found on the label and indicates the"
            " strength of the wine."
        ),
    )
    vintage = forms.IntegerField(
        required=False,
        validators=[
            validators.MinValueValidator(1900),
            validators.MaxValueValidator(datetime.now().year),
        ],
        help_text=_(
            "Enter the year the grapes were harvested to produce the wine. Typically,"
            " vintage years are prominently displayed on wine labels."
        ),
    )
    grapes = OpenMultipleChoiceField(
        required=False,
        queryset=Grape.objects.none(),
        field_name="name",
        help_text=_(
            "Select or add the grape "
            "varieties used"
            "to produce the wine. You can "
            "select multiple options if "
            "applicable."
        ),
    )
    classification = OpenMultipleChoiceField(
        required=False,
        queryset=Classification.objects.none(),
        field_name="name",
        help_text=_(
            "Select or add the classification or designation of the wine, such as "
            "Vin de Table, Vin de Pays, or Appellation d'Origine Contrôlée ("
            "AOC). This helps categorize the wine based on its regional or "
            "quality classification."
        ),
    )
    food_pairings = OpenMultipleChoiceField(
        required=False,
        queryset=FoodPairing.objects.none(),
        field_name="name",
        help_text=_(
            "Enter dishes, cuisines, or ingredients that complement the "
            "flavors of this wine."
        ),
    )
    vineyard = OpenMultipleChoiceField(
        label="Vineyard",
        required=False,
        queryset=Vineyard.objects.none(),
        field_name="name",
        help_text=_("Enter the names of the vineyards which produced the wine."),
    )
    source = OpenMultipleChoiceField(
        required=False,
        queryset=Source.objects.none(),
        field_name="name",
        help_text=_("Where did you get the wine from?"),
    )
    barcode = forms.CharField(
        max_length=100,
        required=False,
        help_text=_("Enter the barcode of the wine as indicated on the label."),
    )
    stock = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(0)],
        help_text=_(
            "Enter the quantity of bottles you currently have in your collection"
        ),
    )
    comment = forms.CharField(
        max_length=250,
        required=False,
        widget=forms.Textarea,
        help_text=_(
            "Share your "
            "thoughts, "
            "tasting "
            "experiences, "
            "or any anecdotes "
            "related to this "
            "wine."
        ),
    )
    rating = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text=_("Rate this wine on a scale from 0 to 10"),
    )
    image = ImageField(
        required=False,
        help_text=_(
            "Upload a photo of the wine bottle or label. Adding an image helps visually"
            " identify the wine in your collection "
        ),
    )

    form_step = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False,
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(4),
        ],
    )


class WineForm(WineBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["form_step"] = 0
        self.set_tom_config(name="grapes", create=True)
        self.set_tom_config(name="classification", create=True)
        self.set_tom_config(name="food_pairings", create=True)
        self.set_tom_config(name="source", create=True)
        self.set_tom_config(name="vineyard", create=True)
        self.set_tom_config(name="country", max_items=1, max_options=-1)
        self.set_tom_config(name="size", max_items=1, max_options=-1)

    def _post_clean(self):
        """Update tom-select config to prevent data loss in the form"""
        if hasattr(self, "cleaned_data"):
            grapes = self.cleaned_data.get("grapes", [])
            if grapes:
                self.set_tom_config(
                    name="grapes",
                    create=True,
                    items=[g.pk for g in grapes],
                    clear=False,
                )
            classifications = self.cleaned_data.get("classification", [])
            if classifications:
                self.set_tom_config(
                    name="classification",
                    create=True,
                    items=[c.pk for c in classifications],
                    clear=False,
                )
            food_pairings = self.cleaned_data.get("food_pairings", [])
            if food_pairings:
                self.set_tom_config(
                    name="food_pairings",
                    create=True,
                    items=[f.pk for f in food_pairings],
                    clear=False,
                )
            source = self.cleaned_data.get("source", [])
            if source:
                self.set_tom_config(
                    name="source",
                    create=True,
                    items=[s.pk for s in source],
                    clear=False,
                )
            vineyard = self.cleaned_data.get("vineyard", [])
            if vineyard:
                self.set_tom_config(
                    name="vineyard",
                    items=[v.pk for v in vineyard],
                    create=True,
                    clear=False,
                )
            country = self.cleaned_data.get("country")
            if country:
                self.set_tom_config(
                    name="country",
                    items=[country],
                    max_items=1,
                    max_options=-1,
                    clear=False,
                )
            size = self.cleaned_data.get("size")
            if size:
                self.set_tom_config(
                    name="size",
                    items=[s.pk for s in size],
                    max_items=1,
                    max_options=-1,
                    clear=False,
                )


class WineEditForm(WineBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial = self.initial

        category = [initial["category"]]
        grapes = [grape.pk for grape in initial["grapes"]]
        classification = [c.pk for c in initial["classification"]]
        food_pairing = [f.pk for f in initial["food_pairings"]]
        source = [s.pk for s in initial["source"]]
        vineyard = [v.pk for v in initial["vineyard"]]
        country = initial["country"]
        size = initial["size"]

        self.fields["category"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {"create": "false", "items": category, "maxItems": 1}
                ),
            }
        )
        self.fields["grapes"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {"create": True, "items": grapes, "maxItems": None}
                ),
            }
        )
        self.fields["classification"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {"create": True, "items": classification, "maxItems": None}
                ),
            }
        )
        self.fields["food_pairings"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {"create": True, "items": food_pairing, "maxItems": None}
                ),
            }
        )
        self.fields["source"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {"create": True, "items": source, "maxItems": None}
                ),
            }
        )
        self.fields["vineyard"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {
                        "create": True,
                        "items": vineyard,
                        "maxItems": None,
                        "maxOptions": None,
                    }
                ),
            }
        )
        self.fields["country"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {
                        "create": False,
                        "items": country,
                        "maxItems": 1,
                        "maxOptions": None,
                    }
                ),
            }
        )
        self.fields["size"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {
                        "create": False,
                        "items": size,
                        "maxItems": 1,
                        "maxOptions": None,
                    }
                ),
            }
        )


class WineFilterForm(TomSelectMixin, forms.Form):
    template_name = "wine_filter_field.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["form_step"] = 0
        self.set_tom_config(name="grapes", create=False)
        self.set_tom_config(name="food_pairings", create=False)
        self.set_tom_config(name="source", create=False)
        self.set_tom_config(name="vineyard", create=False)
        self.set_tom_config(
            name="country", create=False, max_options=-1, placeholder=""
        )
