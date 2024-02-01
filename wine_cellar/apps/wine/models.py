from datetime import datetime

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
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

    def __str__(self):
        if self.name:
            return self.name
        return "no grape"


class Region(models.Model):
    region_id = models.BigIntegerField(null=True)
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)


class Winery(models.Model):
    winery_id = models.BigIntegerField(null=True)
    name = models.CharField(max_length=100)
    website = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)


class Wine(models.Model):
    wine_id = models.BigIntegerField(null=True)
    name = models.CharField(max_length=100)
    wine_type = models.CharField(max_length=2, choices=Categories)
    elaborate = models.CharField(max_length=100)
    grapes = models.ManyToManyField(Grape)
    # FIXME m2m relation
    food_pairing = models.CharField(max_length=100, blank=True)
    body = models.CharField(max_length=100, blank=True)
    acidity = models.CharField(max_length=100, blank=True)
    abv = models.FloatField()
    capacity = models.FloatField(null=True, blank=True)
    vintage = models.PositiveIntegerField(null=True,
        validators=[MinValueValidator(1900), MaxValueValidator(datetime.now().year)],
    )
    comment = models.CharField(max_length=250, blank=True)
    rating = models.PositiveIntegerField(null=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    winery = models.ForeignKey(Winery, on_delete=models.SET_NULL, null=True)

    def get_absolute_url(self):
        return reverse("wine-detail", kwargs={"pk": self.pk})

    @property
    def get_grapes(self):
        print(self.grapes)
        return "".join([str(grape) for grape in self.grapes.all()])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "wine_type", "abv", "capacity", "vintage"],
                name="unique wine",
            )
        ]




class Tag(models.Model):
    name = models.CharField(max_length=100)
