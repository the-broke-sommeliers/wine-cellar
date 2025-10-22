from django import forms
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
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        user_fields = ["storage"]
        for user_field in user_fields:
            self.fields[user_field].queryset = self.fields[
                user_field
            ].queryset.model.objects.filter(user=self.user)
            self.fields[user_field].user = self.user

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

    def clean_row(self):
        row = self.cleaned_data.get("row")
        storage = self.cleaned_data.get("storage")
        if storage and row:
            if storage.rows == 0:
                raise forms.ValidationError(
                    _("The selected storage has no rows."), code="redundant_row"
                )
            if row > storage.rows:
                raise forms.ValidationError(
                    _("The selected row exceeds the number of rows in the storage."),
                    code="row_exceeds",
                )
        return row

    def clean_column(self):
        column = self.cleaned_data.get("column")
        storage = self.cleaned_data.get("storage")
        if storage and column:
            if storage.columns == 0:
                raise forms.ValidationError(
                    _("The selected storage has no columns."), code="redundant_column"
                )
            if column > storage.columns:
                raise forms.ValidationError(
                    _(
                        "The selected column exceeds the number of columns in the"
                        " storage."
                    ),
                    code="column_exceeds",
                )
        return column

    def clean(self):
        cleaned_data = super().clean()
        row = cleaned_data.get("row")
        column = cleaned_data.get("column")
        storage = cleaned_data.get("storage")
        if storage:
            if storage.rows > 0 and storage.columns > 0:
                if not row or not column:
                    raise forms.ValidationError(
                        _(
                            "Both row and column must be specified for the selected"
                            " storage."
                        ),
                        code="row_column_required",
                    )
                if storage.is_slot_occupied(row, column):
                    raise forms.ValidationError(
                        _(
                            "The selected slot (row: %(row)s, column: %(column)s)"
                            " is already occupied in the storage."
                        ),
                        code="slot_occupied",
                        params={"row": row, "column": column},
                    )
        return cleaned_data
