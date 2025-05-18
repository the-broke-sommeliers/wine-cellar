from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models


class UserSettings(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="user_settings",
    )
    language = models.CharField(
        max_length=7,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
    )
    currency = models.CharField(
        max_length=3, choices=settings.CURRENCIES, default="EUR"
    )
