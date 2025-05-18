from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.user.models import UserSettings


class UserSettingsForm(ModelForm):
    class Meta:
        model = UserSettings
        fields = ["language", "currency"]
        help_texts = {
            "language": _("The language the site is displayed in."),
            "currency": _("The default currency used for the price of a wine."),
        }
