import json

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.storage.models import Storage
from wine_cellar.apps.user.views import get_user_settings


class StorageForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label=_("Storage Name"),
        help_text=_("Enter the name of the storage."),
    )
    description = forms.CharField(
        required=False,
        label=_("Storage Description"),
        help_text=_("Enter a description of the storage."),
    )
    location = forms.CharField(
        max_length=100,
        label=_("Location"),
        help_text=_("Enter the location of the storage."),
    )
    rows = forms.IntegerField(
        min_value=0,
        required=False,
        label=_("Number of Rows"),
        help_text=_("Enter the number of rows in the storage."),
    )
    columns = forms.IntegerField(
        min_value=0,
        required=False,
        label=_("Number of Columns"),
        help_text=_("Enter the number of columns in the storage."),
    )
    swap_axes = forms.BooleanField(
        required=False,
        label=_("Show Columns First"),
        help_text=_(
            "Group the storage view by column instead of row, e.g. if you"
            " organize by column rather than by shelf."
        ),
    )
    row_labels_enabled = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Show Row Labels"),
        help_text=_('Display and allow naming individual rows (e.g. "Top Shelf").'),
    )
    column_labels_enabled = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Show Column Labels"),
        help_text=_('Display and allow naming individual columns (e.g. "Left Bin").'),
    )


class StockForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.storage_item = kwargs.pop("storage_item", None)
        super().__init__(*args, **kwargs)
        user_fields = ["storage"]
        for user_field in user_fields:
            self.fields[user_field].queryset = self.fields[
                user_field
            ].queryset.model.objects.filter(user=self.user)
            self.fields[user_field].user = self.user
        user_settings = get_user_settings(self.user)
        self.fields["price"].help_text = _(
            "Enter the price of the bottle in %(currency)s."
        ) % {"currency": settings.CURRENCY_SYMBOLS[user_settings.currency]}

    storage = forms.ModelChoiceField(
        queryset=Storage.objects.none(),
        help_text=_("Enter the name of the storage."),
    )
    quantity = forms.IntegerField(
        required=False,
        min_value=1,
        initial=1,
        label=_("Quantity"),
        help_text=_("How many bottles to add."),
    )
    slots = forms.CharField(required=False, widget=forms.HiddenInput())
    price = forms.DecimalField(
        required=False,
        max_digits=6,
        decimal_places=2,
        localize=True,
    )

    def clean_slots(self):
        raw_slots = self.cleaned_data.get("slots")
        try:
            slots = json.loads(raw_slots) if raw_slots else []
        except (TypeError, ValueError):
            raise forms.ValidationError(
                _("Invalid slot selection."), code="invalid_slots"
            )
        if not isinstance(slots, list) or not all(
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(value, int) for value in pair)
            for pair in slots
        ):
            raise forms.ValidationError(
                _("Invalid slot selection."), code="invalid_slots"
            )
        pairs = [tuple(pair) for pair in slots]
        if len(pairs) != len(set(pairs)):
            raise forms.ValidationError(
                _("The same slot was selected more than once."),
                code="duplicate_slot",
            )
        return pairs

    def clean(self):
        cleaned_data = super().clean()
        storage = cleaned_data.get("storage")
        slots = cleaned_data.get("slots")
        if not storage or slots is None:
            return cleaned_data

        if self.storage_item is None:
            # Adding one or more new bottles.
            if storage.is_unlimited:
                # Defaults to a single bottle if left blank.
                cleaned_data["quantity"] = cleaned_data.get("quantity") or 1
            elif not slots:
                raise forms.ValidationError(
                    _("Select at least one slot."), code="no_slots_selected"
                )
            elif not set(slots) <= set(storage.free_slots()):
                raise forms.ValidationError(
                    _(
                        "One or more of the selected slots are no longer free."
                        " Please reselect."
                    ),
                    code="slot_occupied",
                )
        else:
            # Moving/editing an existing bottle.
            if storage.is_unlimited:
                if slots:
                    raise forms.ValidationError(
                        _("The selected storage has no rows or columns."),
                        code="redundant_slot",
                    )
            elif len(slots) != 1:
                raise forms.ValidationError(
                    _("Select a slot for this bottle."), code="no_slots_selected"
                )
            elif not set(slots) <= set(
                storage.free_slots(exclude_item=self.storage_item)
            ):
                row, column = slots[0]
                raise forms.ValidationError(
                    _(
                        "The selected slot (row: %(row)s, column: %(column)s)"
                        " is already occupied in the storage."
                    ),
                    code="slot_occupied",
                    params={"row": row, "column": column},
                )
        return cleaned_data


class StockOpenForm(forms.Form):
    note = forms.CharField(
        label=_("Note"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("Why are you opening this bottle? (e.g. birthday dinner)"),
    )
    drink_in_days = forms.IntegerField(
        label=_("Drink Reminder"),
        required=False,
        min_value=1,
        help_text=_(
            "Send a reminder to drink the rest of this bottle by this many days."
        ),
    )
