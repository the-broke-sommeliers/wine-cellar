import pycountry
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import ImageField
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


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


class Category(models.TextChoices):
    DRY = "DR", _("Dry")
    SEMI_DRY = "SD", _("Semi-Dry")
    MEDIUM_SWEET = "MS", _("Medium Sweet")
    SWEET = "SW", _("Sweet")
    FEINHERB = "FH", _("Feinherb")


class Size(UserContentModel):
    name = models.FloatField()

    def __str__(self):
        return str(self.name)


class Grape(UserContentModel):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
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
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique food pairing",
            )
        ]

    def __str__(self):
        return self.name


class Classification(UserContentModel):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique classification",
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
    classification = models.ManyToManyField(Classification)
    food_pairings = models.ManyToManyField(FoodPairing)
    abv = models.FloatField(null=True, blank=True)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True)
    vintage = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)],
        null=True,
    )
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
    stock = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )

    def get_absolute_url(self):
        return reverse("wine-detail", kwargs={"pk": self.pk})

    @property
    def get_vineyards(self):
        return "\n".join([str(vineyard) for vineyard in self.vineyard.all()])

    @property
    def get_grapes(self):
        return ", ".join([str(grape) for grape in self.grapes.all()])

    @property
    def get_classifications(self):
        return "\n".join(
            [str(classification) for classification in self.classification.all()]
        )

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
    def get_type_image(self):
        match self.wine_type:
            case WineType.RED:
                return static("images/red_glass_no_ice_no_shadow.svg")
            case WineType.WHITE:
                return static("images/white_glass.svg")
            case _:
                return static("images/white_glass.svg")

    @property
    def image(self):
        i = self.wineimage_set.first()
        if not i:
            return static("images/bottle.svg")
        return i.image.url

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
                ],
                name="unique wine",
            )
        ]


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "user_{0}/{1}".format(instance.user.pk, filename)


class WineImage(models.Model):
    image = ImageField(upload_to=user_directory_path)
    wine = models.ForeignKey(Wine, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
