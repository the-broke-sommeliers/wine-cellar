from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

# Keep in sync with the .wine-list--max-cols-N classes in forms.css.
MAX_WINES_PER_ROW_CHOICES = [
    (0, _("Automatic")),
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
    (5, "5"),
]


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
    notifications = models.BooleanField(default=True)
    max_wines_per_row = models.PositiveSmallIntegerField(
        choices=MAX_WINES_PER_ROW_CHOICES, default=0
    )
    compact_wine_list = models.BooleanField(default=False)
    last_seen_whats_new_version = models.CharField(
        max_length=20, blank=True, default=""
    )
