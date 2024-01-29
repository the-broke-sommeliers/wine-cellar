from datetime import datetime

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
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


class Wine(models.Model):
    name = models.CharField(max_length=100)
    wine_type = models.CharField(max_length=2, choices=Categories)
    abv = models.FloatField()
    capacity = models.FloatField()
    vintage = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(datetime.now().year)],
    )
    comment = models.CharField(max_length=250, blank=True)

    def get_absolute_url(self):
        return reverse("wine-detail", kwargs={"pk": self.pk})

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'wine_type', 'abv', 'capacity', 'vintage'], name='unique appversion')
        ]


class Rating(models.Model):
    value = models.PositiveIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10)],
    )
    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name='rating')
    user = models.ForeignKey(User, on_delete=models.CharField)


class Winery(models.Model):
    name = models.CharField(max_length=100)


class Location(models.Model):
    name = models.CharField(max_length=100)


class Tag(models.Model):
    name = models.CharField(max_length=100)
