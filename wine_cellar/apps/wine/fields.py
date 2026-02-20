from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _


class OpenMultipleChoiceField(ModelMultipleChoiceField):
    """ModelMultipleChoiceField which allows adding new values

    Parameters:
        field_name: String
          The name of the field from the associated model which
           will be used to create it.
    """

    user = None

    def __init__(self, queryset, field_name, field_class=None, **kwargs):
        super().__init__(queryset, **kwargs)
        self.field_name = field_name
        self.field_class = field_class
        self.new_values = []

        self.default_error_messages.update(
            {
                "invalid_new_value": _("'%(pk)s' is not a valid value."),
            }
        )

    def clean(self, value):
        if not value:
            return super().clean(value)

        self.new_values = []
        existing_ids = []

        for v in value:
            if not v:
                continue
            if isinstance(v, str) and v.startswith("tom_new_opt"):
                new_val = v.removeprefix("tom_new_opt")

                if self.field_class:
                    try:
                        new_val = self.field_class(new_val)
                    except ValueError:
                        raise ValidationError(
                            self.error_messages["invalid_new_value"],
                            code="invalid_new_value",
                            params={"value": v},
                        )

                self.new_values.append(new_val)

            else:
                try:
                    existing_ids.append(int(v))
                except (ValueError, TypeError):
                    raise ValidationError(
                        self.error_messages["invalid_choice"],
                        code="invalid_choice",
                        params={"value": v},
                    )

        qs = super().clean(existing_ids) if existing_ids else self.queryset.none()
        if self.required and not existing_ids and not self.new_values:
            raise ValidationError(self.error_messages["required"], code="required")

        return qs


class OpenChoiceModelFormViewMixin:

    def create_new_objects(self, form):
        cleaned = form.cleaned_data

        for name, field in form.fields.items():
            if not isinstance(field, OpenMultipleChoiceField):
                continue

            qs = cleaned.get(name)
            if qs is None:
                continue

            new_objs = []
            for val in set(field.new_values):
                obj, _ = field.queryset.get_or_create(
                    **{field.field_name: val, "user": getattr(field, "user", None)}
                )
                new_objs.append(obj)
            cleaned[name] = list(qs) + new_objs

        return cleaned
