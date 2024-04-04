import json
from datetime import datetime

from django import forms
from django.core import validators
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import ImageField
from django.utils.translation import gettext as _

from wine_cellar.apps.wine.fields import OpenMultipleChoiceField
from wine_cellar.apps.wine.models import (
    Category,
    Classification,
    FoodPairing,
    Grape,
    WineType,
)


class WineForm(forms.Form):
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
    stock = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(0)],
        help_text=_(
            "Enter the quantity of bottles you currently have in your collection"
        ),
    )
    grapes.widget.attrs.update(
        {
            "data-tom_config": json.dumps({"create": True, "maxItems": None}),
            "clear": "true",
        }
    )
    classification.widget.attrs.update(
        {
            "data-tom_config": json.dumps({"create": True, "maxItems": None}),
            "clear": "true",
        }
    )
    food_pairings.widget.attrs.update(
        {
            "data-tom_config": json.dumps({"create": True, "maxItems": None}),
            "clear": "true",
        }
    )


class WineFilterForm(forms.Form):
    template_name = "wine_filter_field.html"
