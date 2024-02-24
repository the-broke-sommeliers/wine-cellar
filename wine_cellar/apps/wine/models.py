from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import ImageField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Categories(models.TextChoices):
    WHITE = "WH", _("White")
    RED = "RE", _("Red")
    ROSE = "RO", _("Rose")
    SPARKLING = "SP", _("Sparkling")
    DESSERT = "DE", _("Dessert")
    FORTIFIED = "FO", _("Fortified")


class Grape(models.Model):
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
        return "no grape"


class Region(models.Model):
    region_id = models.BigIntegerField(null=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "country"],
                name="unique region",
            )
        ]

    def __str__(self):
        return self.name


class Winery(models.Model):
    winery_id = models.BigIntegerField(null=True)
    name = models.CharField(max_length=100)
    website = models.CharField(max_length=100, null=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "region"],
                name="unique winery",
            )
        ]

    def __str__(self):
        return self.name


class Vintage(models.Model):
    name = models.PositiveIntegerField(
        primary_key=True,
        validators=[MinValueValidator(1900), MaxValueValidator(datetime.now().year)],
    )

    def __str__(self):
        return str(self.name)


class FoodPairing(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="unique food pairing",
            )
        ]

    def __str__(self):
        return self.name


class Classification(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="unique classification",
            )
        ]

    def __str__(self):
        return self.name


class Wine(models.Model):
    wine_id = models.BigIntegerField(null=True)
    name = models.CharField(max_length=100)
    wine_type = models.CharField(max_length=2, choices=Categories)
    elaborate = models.CharField(max_length=100, null=True, blank=True)
    grapes = models.ManyToManyField(Grape)
    classification = models.ManyToManyField(Classification)
    food_pairings = models.ManyToManyField(FoodPairing)
    body = models.CharField(max_length=100, blank=True)
    acidity = models.CharField(max_length=100, blank=True)
    abv = models.FloatField()
    capacity = models.FloatField(null=True, blank=True)
    vintage = models.ManyToManyField(Vintage)
    comment = models.CharField(max_length=250, blank=True)
    rating = models.PositiveIntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    winery = models.ForeignKey(Winery, on_delete=models.SET_NULL, null=True)

    def get_absolute_url(self):
        return reverse("wine-detail", kwargs={"pk": self.pk})

    @property
    def get_grapes(self):
        return "".join([str(grape) for grape in self.grapes.all()])

    @property
    def get_vintages(self):
        return "".join([str(vintage) for vintage in self.vintage.all()])

    @property
    def image(self):
        i = self.wineimage_set.first()
        return i

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "wine_type", "abv", "capacity", "winery"],
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
