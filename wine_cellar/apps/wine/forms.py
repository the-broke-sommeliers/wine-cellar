import json
from datetime import datetime

import pycountry
from django import forms
from django.core import validators
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import ImageField, model_to_dict
from django.utils.translation import gettext as _

from wine_cellar.apps.wine.fields import OpenMultipleChoiceField
from wine_cellar.apps.wine.models import (
    Category,
    Classification,
    FoodPairing,
    Grape,
    WineType,
)


class WineBaseForm(forms.Form):
    class Meta:
        abstract = True

    name = forms.CharField(
        max_length=100,
        help_text=_("Enter the name of the wine as indicated on the label."),
    )
    wine_type = forms.CharField(
        max_length=2,
        widget=forms.Select(choices=WineType),
        help_text=_("Select the category that best describes the type of wine. "),
    )
    category = forms.CharField(
        max_length=2,
        widget=forms.Select(choices=Category),
        help_text=_("Select the category of the wine."),
    )
    abv = forms.FloatField(
        help_text=_(
            "Please enter the percentage of alcohol in the"
            " wine. This information is typically found on the label and indicates the"
            " strength of the wine."
        )
    )
    capacity = forms.FloatField(
        help_text=_("Please enter the volume of the wine bottle in liters, e.g. 0.75.")
    )

    vintage = forms.IntegerField(
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
        queryset=Grape.objects.all(),
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
        queryset=Classification.objects.all(),
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
        queryset=FoodPairing.objects.all(),
        field_name="name",
        help_text=_(
            "Enter dishes, cuisines, or ingredients that complement the "
            "flavors of this wine."
        ),
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
    remove_background = forms.BooleanField(
        required=False, help_text=_("Remove background from image")
    )
    image = ImageField(
        required=False,
        help_text=_(
            "Upload a photo of the wine bottle or label. Adding an image helps visually"
            " identify the wine in your collection "
        ),
    )

    def set_tom_config(
        self, name, create=False, items=[], max_items=None, max_options=50, clear=True
    ):
        tom_config = {"create": create, "maxItems": max_items}
        if items:
            tom_config["items"] = items
        if max_options:
            tom_config["max_options"] = max_options
        self.fields[name].widget.attrs.update(
            {
                "data-tom_config": json.dumps(tom_config),
                "data-clear": "true" if clear else "",
            }
        )


class WineForm(WineBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_tom_config(name="grapes", create=True)
        self.set_tom_config(name="classification", create=True)
        self.set_tom_config(name="food_pairings", create=True)
        self.set_tom_config(name="country", max_items=1, max_options=None)

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
        self.set_tom_config(name="country", max_items=1, max_options=None, clear=False)


class WineEditForm(WineBaseForm):
    def __init__(self, instance, *args, **kwargs):
        initial = model_to_dict(instance)
        super(forms.Form, self).__init__(initial, *args, **kwargs)

        category = [initial["category"]]
        grapes = [grape.pk for grape in initial["grapes"]]
        classification = [c.pk for c in initial["classification"]]
        food_pairing = [f.pk for f in initial["food_pairings"]]

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

        self.fields["country"].widget.attrs.update(
            {
                "data-tom_config": json.dumps(
                    {
                        "create": False,
                        "items": [instance.country],
                        "maxItems": 1,
                        "maxOptions": None,
                    }
                ),
            }
        )


class WineFilterForm(forms.Form):
    template_name = "wine_filter_field.html"
