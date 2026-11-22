from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.user.models import UserSettings


class UserSettingsForm(ModelForm):

    class Meta:
        model = UserSettings
        fields = [
            "language",
            "currency",
            "max_wines_per_row",
            "compact_wine_list",
            "notifications",
        ]
        labels = {
            "language": _("Language"),
            "currency": _("Currency"),
            "max_wines_per_row": _("Wines per Row"),
            "compact_wine_list": _("Compact Wine List"),
            "notifications": _("Email Notifications"),
        }
        help_texts = {
            "language": _("The language the site is displayed in."),
            "currency": _("The default currency used for the price of a wine."),
            "max_wines_per_row": _(
                "The maximum number of wines shown next to each other in the"
                " wine list. Narrower screens may show fewer."
            ),
            "compact_wine_list": _(
                "On wide screens, keep the wine cards at a compact size and"
                " center the wine list instead of using the full width."
            ),
            "notifications": _("Receive email notifications."),
        }
