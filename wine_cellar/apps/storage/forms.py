from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.storage.models import Storage


class StorageForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        help_text=_("Enter the name of the storage."),
    )
    description = forms.CharField(
        required=False,
        help_text=_("Enter a description of the storage."),
    )
    location = forms.CharField(
        max_length=100,
        help_text=_("Enter the location of the storage."),
    )
    rows = forms.IntegerField(
        min_value=0,
        required=False,
        help_text=_("Enter the number of rows in the storage."),
    )
    columns = forms.IntegerField(
        min_value=0,
        required=False,
        help_text=_("Enter the number of columns in the storage."),
    )


class StockAddForm(forms.Form):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        user_fields = ["storage"]
        for user_field in user_fields:
            self.fields[user_field].queryset = self.fields[
                user_field
            ].queryset.model.objects.filter(Q(user=None) | Q(user=user))
            self.fields[user_field].user = user

    storage = forms.ModelChoiceField(
        queryset=Storage.objects.none(),
        help_text=_("Enter the name of the storage."),
    )
    row = forms.IntegerField(
        required=False,
        min_value=0,
        help_text=_("Enter the number of rows in the storage."),
        widget=forms.Select(),
    )
    column = forms.IntegerField(
        required=False,
        min_value=0,
        help_text=_("Enter the number of columns in the storage."),
        widget=forms.Select(),
    )
