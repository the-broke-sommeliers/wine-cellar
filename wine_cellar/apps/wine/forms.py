import json
from datetime import datetime

import pycountry
from django import forms
from django.conf import settings
from django.core import validators
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Q, QuerySet
from django.forms import DateField, ImageField
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.wine.fields import OpenMultipleChoiceField
from wine_cellar.apps.wine.models import (
    Appellation,
    Attribute,
    Category,
    FoodPairing,
    Grape,
    ImageType,
    Region,
    Size,
    Source,
    Vineyard,
    WineImage,
    WineType,
)
from wine_cellar.apps.wine.widgets import (
    MapChoosePointWidget,
    NoFilenameClearableFileInput,
)

image_fields_map = {
    "image_front": ImageType.FRONT,
    "image_back": ImageType.BACK,
    "image_front_label": ImageType.LABEL_FRONT,
    "image_back_label": ImageType.LABEL_BACK,
}


TOM_FIELDS = {
    "grapes": {"create": True},
    "attributes": {"create": True},
    "food_pairings": {"create": True},
    "source": {"create": True},
    "vineyard": {"create": True},
    "country": {"max_items": 1, "max_options": -1},
    "region": {"create": True, "max_items": 1, "max_options": -1},
    "appellation": {"create": True, "max_items": 1, "max_options": -1},
    "size": {"max_items": 1, "max_options": -1},
}


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
        clear = False if items else clear
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


class WineFormPostCleanMixin:
    def _post_clean(self):
        if not hasattr(self, "cleaned_data"):
            return

        fields_to_update = [
            "grapes",
            "attributes",
            "food_pairings",
            "source",
            "vineyard",
            "country",
            "region",
            "appellation",
            "size",
        ]

        for name in fields_to_update:
            value = self.cleaned_data.get(name)
            if not value:
                continue

            if isinstance(value, list) or isinstance(value, QuerySet):
                items = [v.pk if hasattr(v, "pk") else v for v in value]
            else:
                items = [value.pk if hasattr(value, "pk") else value]

            create = name in (
                "grapes",
                "attributes",
                "food_pairings",
                "source",
                "vineyard",
                "region",
                "appellation",
            )
            max_items = (
                1 if name in ("country", "region", "appellation", "size") else None
            )
            max_options = (
                -1 if name in ("country", "region", "appellation", "size") else 50
            )

            self.set_tom_config(
                name=name,
                items=items,
                create=create,
                max_items=max_items,
                max_options=max_options,
                clear=False,
            )


class WineForm(TomSelectMixin, WineFormPostCleanMixin, forms.Form):

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial["form_step"] = 0
        if user:
            self._limit_user_querysets(user)
            self._set_currency_help(user)

        self._init_tomselect()
        self._init_existing_images()

    def _limit_user_querysets(self, user):

        fields = [
            "vineyard",
            "attributes",
            "grapes",
            "food_pairings",
            "source",
            "size",
            "region",
            "appellation",
        ]

        for name in fields:
            field = self.fields[name]
            model = field.queryset.model

            field.queryset = model.objects.filter(Q(user=None) | Q(user=user))

            field.user = user

    def _set_currency_help(self, user):

        settings_obj = get_user_settings(user)

        self.fields["price"].help_text = _(
            "Enter the price of the bottle in %(currency)s."
        ) % {"currency": settings.CURRENCY_SYMBOLS[settings_obj.currency]}

    def _init_tomselect(self):
        for name, config in TOM_FIELDS.items():

            if name not in self.fields:
                continue

            value = self.initial.get(name)

            if isinstance(value, list):
                items = [v.pk if hasattr(v, "pk") else v for v in value]
            elif value:
                items = [value.pk if hasattr(value, "pk") else value]
            else:
                items = []

            self.set_tom_config(name=name, items=items, **config)

    def _init_existing_images(self):

        wine_id = self.initial.get("id")

        if not wine_id:
            return

        for field_name, image_type in image_fields_map.items():

            image = (
                WineImage.objects.filter(
                    wine=wine_id,
                    image_type=image_type,
                )
                .order_by("-id")
                .first()
            )

            if image:
                self.initial[field_name] = image.thumbnail
                self.fields[field_name].widget.attrs[
                    "data-existing-url"
                ] = image.thumbnail.url

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
            "Select the country the wine was produced in as indicated on the label."
        ),
    )
    region = OpenMultipleChoiceField(
        required=False,
        field_name="name",
        queryset=Region.objects.none(),
        help_text=_("Enter the name of the region the wine is from."),
    )
    appellation = OpenMultipleChoiceField(
        required=False,
        field_name="name",
        queryset=Appellation.objects.none(),
        help_text=_("Enter the name of the appellation of the wine."),
    )
    location = forms.JSONField(
        required=False,
        max_length=500,
        help_text=_(
            "Select the location (region, vineyard, site) the wine is from."
            " Click inside the map to set a marker. The "
            "marker can be dragged when pressed."
        ),
        widget=MapChoosePointWidget(polygon=None),
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
        localize=True,
        # Force number input on mobile devices
        widget=forms.NumberInput(
            attrs={
                "step": "0.1",
                "inputmode": "decimal",
                "pattern": r"\d+(\.\d+)?",
            }
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
            "Select or add the grape varieties used to produce the wine. You can "
            "select multiple options if applicable."
        ),
    )
    attributes = OpenMultipleChoiceField(
        required=False,
        queryset=Attribute.objects.none(),
        field_name="name",
        help_text=_(
            "Add any attributes that apply to this wine, such as"
            " natural, retsina or organic."
        ),
    )
    drink_by = DateField(
        required=False,
        help_text=_("Select the date this wine should be drunk by."),
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        localize=True,
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
    price = forms.DecimalField(
        required=False,
        max_digits=6,
        decimal_places=2,
        localize=True,
        # Force number input on mobile devices
        widget=forms.NumberInput(
            attrs={
                "step": "0.01",
                "inputmode": "decimal",
                "pattern": r"\d+(\.\d+)?",
            }
        ),
    )
    barcode = forms.CharField(
        max_length=100,
        required=False,
        help_text=_(
            "Enter the barcode number of the wine as indicated"
            " on the label or scan using the button below."
        ),
    )
    comment = forms.CharField(
        max_length=250,
        required=False,
        widget=forms.Textarea,
        help_text=_(
            "Share your thoughts, tasting experiences, or any anecdotes"
            " related to this wine."
        ),
    )
    rating = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text=_("Rate this wine on a scale from 0 to 10."),
    )
    image_front = ImageField(
        widget=NoFilenameClearableFileInput(attrs={"accept": "image/*"}),
        required=False,
        help_text=_("Upload a photo of the front of the wine bottle."),
    )
    image_back = ImageField(
        widget=NoFilenameClearableFileInput(attrs={"accept": "image/*"}),
        required=False,
        help_text=_("Upload a photo of the back of the wine bottle."),
    )
    image_front_label = ImageField(
        widget=NoFilenameClearableFileInput(attrs={"accept": "image/*"}),
        required=False,
        help_text=_("Upload a photo of the front of the bottle label."),
    )
    image_back_label = ImageField(
        widget=NoFilenameClearableFileInput(attrs={"accept": "image/*"}),
        required=False,
        help_text=_("Upload a photo of the back of the bottle label."),
    )
    form_step = forms.IntegerField(
        widget=forms.HiddenInput(),
        label="",
        required=False,
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(5),
        ],
    )


class WineFilterForm(TomSelectMixin, WineFormPostCleanMixin, forms.Form):
    template_name = "wine_filter_field.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["form_step"] = 0
        self.set_tom_config(name="grapes", create=False)
        self.set_tom_config(name="food_pairings", create=False)
        self.set_tom_config(name="source", create=False)
        self.set_tom_config(name="vineyard", create=False)
        self.set_tom_config(name="attributes", create=False)
        self.set_tom_config(
            name="country", create=False, max_options=-1, placeholder=""
        )


class WineUploadAIForm(forms.Form):
    template_name = "wine_filter_field.html"

    front = forms.ImageField(
        widget=NoFilenameClearableFileInput(attrs={"accept": "image/*"}),
        required=False,
        help_text=_("Upload an image of the front label."),
    )
    back = ImageField(
        widget=NoFilenameClearableFileInput(attrs={"accept": "image/*"}),
        required=False,
        help_text=_("Upload an image of the back label."),
    )

    def clean(self):
        cleaned_data = super().clean()
        front = cleaned_data.get("front")
        back = cleaned_data.get("back")
        if not front and not back:
            raise forms.ValidationError(
                _("At least one image (front or back) must be uploaded.")
            )
        return cleaned_data
