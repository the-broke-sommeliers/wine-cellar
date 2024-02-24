from datetime import datetime

from django import forms
from django.core import validators
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import ClearableFileInput

from wine_cellar.apps.wine.models import Categories


class WineForm(forms.Form):
    name = forms.CharField(max_length=100)
    wine_type = forms.CharField(max_length=2, widget=forms.Select(choices=Categories))
    abv = forms.FloatField()
    capacity = forms.FloatField()
    vintage = forms.IntegerField(
        validators=[
            validators.MinValueValidator(1900),
            validators.MaxValueValidator(datetime.now().year),
        ],
    )
    comment = forms.CharField(max_length=250, required=False, widget=forms.Textarea)
    rating = forms.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    image = ClearableFileInput()
