import pycountry
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.wine.utils import user_directory_path


class UserContentModel(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WineType(models.TextChoices):
    WHITE = "WH", _("White")
    RED = "RE", _("Red")
    ROSE = "RO", _("Rose")
    SPARKLING = "SP", _("Sparkling")
    DESSERT = "DE", _("Dessert")
    FORTIFIED = "FO", _("Fortified")
    ORANGE = "OR", _("Orange")


class Category(models.TextChoices):
    DRY = "DR", _("Dry")
    SEMI_DRY = "SD", _("Semi-Dry")
    MEDIUM_SWEET = "MS", _("Medium Sweet")
    SWEET = "SW", _("Sweet")
    FEINHERB = "FH", _("Feinherb")


class ImageType(models.TextChoices):
    FRONT = "FR", _("Front")
    BACK = "BA", _("Back")
    LABEL_FRONT = "LF", _("Label Front")
    LABEL_BACK = "LB", _("Label Back")


class Size(UserContentModel):
    name = models.FloatField(verbose_name=_("Size"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique size",
            )
        ]

    def __str__(self):
        return str(number_format(self.name, use_l10n=True))


class Grape(UserContentModel):
    name = models.CharField(max_length=100, verbose_name=_("Grape"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique grape",
            )
        ]

    def __str__(self):
        if self.name:
            return self.name
        return ""


class Vineyard(UserContentModel):
    name = models.CharField(max_length=100)
    website = models.CharField(max_length=100, null=True)
    region = models.CharField(max_length=250, null=True)
    country = models.CharField(
        max_length=3,
        null=True,
        choices={country.alpha_2: country.name for country in pycountry.countries},
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "country", "region", "user"],
                name="unique vineyard",
            )
        ]

    def __str__(self):
        return self.name


class FoodPairing(UserContentModel):
    name = models.CharField(max_length=100, verbose_name=_("Food"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique food pairing",
            )
        ]

    def __str__(self):
        return self.name


class Attribute(UserContentModel):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique attributes",
            )
        ]

    def __str__(self):
        return self.name


class Source(UserContentModel):
    name = models.CharField(max_length=250)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique source",
            )
        ]

    def __str__(self):
        return self.name


class Wine(UserContentModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    barcode = models.CharField(max_length=100, null=True)
    wine_type = models.CharField(max_length=2, choices=WineType)
    category = models.CharField(max_length=2, choices=Category, null=True)
    grapes = models.ManyToManyField(Grape)
    attributes = models.ManyToManyField(Attribute)
    food_pairings = models.ManyToManyField(FoodPairing)
    abv = models.FloatField(null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True)
    vintage = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)],
        null=True,
    )
    drink_by = models.DateField(blank=True, null=True)
    comment = models.CharField(max_length=250, blank=True)
    rating = models.PositiveIntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    country = models.CharField(
        max_length=3,
        choices={country.alpha_2: country.name for country in pycountry.countries},
    )
    vineyard = models.ManyToManyField(Vineyard)
    source = models.ManyToManyField(Source)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True)

    def get_absolute_url(self):
        return reverse("wine-detail", kwargs={"pk": self.pk})

    @property
    def get_vineyards(self):
        return "\n".join([str(vineyard) for vineyard in self.vineyard.all()])

    @property
    def get_grapes(self):
        return ", ".join([str(grape) for grape in self.grapes.all()])

    @property
    def get_sources(self):
        return ", ".join([str(s) for s in self.source.all()])

    @property
    def get_attributes(self):
        return "\n".join([str(attribute) for attribute in self.attributes.all()])

    @property
    def get_price_with_currency(self):
        currency = settings.CURRENCY_SYMBOLS.get(
            getattr(self.user.user_settings, "currency", "EUR"), "€"
        )
        formatted_price = number_format(self.price, use_l10n=True)
        return f"{formatted_price}{currency}"

    @property
    def get_food_pairings(self):
        return "\n".join([str(pairing) for pairing in self.food_pairings.all()])

    @property
    def get_type(self):
        return WineType(self.wine_type).label

    @property
    def get_category(self):
        if self.category:
            return Category(self.category).label

    @property
    def total_stock(self):
        return self.storageitem_set.filter(deleted=False).count()

    @property
    def get_stock(self):
        return self.storageitem_set.filter(deleted=False)

    @property
    def image(self):
        i = self.wineimage_set.first()
        if not i:
            return static("images/bottle.svg")
        return i.image.url

    @property
    def image_thumbnail(self):
        i = self.wineimage_set.filter(image_type=ImageType.FRONT)
        if not i:
            return static("images/bottle.svg")
        front = i.first()
        if front.thumbnail:
            return front.thumbnail.url
        # return normal image as fallback
        return front.image.url

    @property
    def image_thumbnails(self):
        images = {img.image_type: img for img in self.wineimage_set.all()}
        order = [
            ImageType.FRONT,
            ImageType.BACK,
            ImageType.LABEL_FRONT,
            ImageType.LABEL_BACK,
        ]
        result = []
        for image_type in order:
            image = images.get(image_type)
            if image:
                src = image.thumbnail.url if image.thumbnail else image.image.url
                result.append(src)
        return result

    @property
    def country_name(self):
        return pycountry.countries.get(alpha_2=self.country).name

    @property
    def country_icon(self):
        return pycountry.countries.get(alpha_2=self.country).flag

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "name",
                    "wine_type",
                    "abv",
                    "size",
                    "vintage",
                    "country",
                    "user",
                ],
                name="unique wine",
            )
        ]


class WineImage(models.Model):
    image = models.ImageField(upload_to=user_directory_path)
    thumbnail = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    wine = models.ForeignKey(Wine, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    image_type = models.CharField(
        max_length=3, choices=ImageType, default=ImageType.FRONT
    )
