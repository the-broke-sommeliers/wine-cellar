from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField


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
        self.field_class = field_class if field_class else None

    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages["required"], code="required")

    # code taken from ModelMultipleChoiceField with addition of creating a
    def _check_values(self, value):
        """
        Given a list of possible PK values, return a QuerySet of the
        corresponding objects. If a value is not a PK, create a new object.
        Raise a ValidationError if a given value is invalid
         (not a valid PK, not in the queryset, etc.)
        """
        key = self.to_field_name or "pk"
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            value = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages["invalid_list"],
                code="invalid_list",
            )
        new_values = set()
        for pk in value:
            try:
                self.queryset.filter(**{key: pk})
                new_values.add(pk)
            except ValueError:
                # assume not a pk but a new value
                if isinstance(pk, str) and pk.startswith("tom_new_opt"):
                    v = pk.removeprefix("tom_new_opt")
                    if self.field_class:
                        v = self.field_class(v)
                    new_value, _ = self.queryset.get_or_create(
                        **{self.field_name: v, "user": self.user}
                    )
                    new_values.add(new_value.pk)
                elif isinstance(pk, str) and not self.required and pk == "":
                    continue
                else:
                    raise ValidationError(
                        self.error_messages["invalid_pk_value"],
                        code="invalid_pk_value",
                        params={"pk": pk},
                    )
            except TypeError:
                raise ValidationError(
                    self.error_messages["invalid_pk_value"],
                    code="invalid_pk_value",
                    params={"pk": pk},
                )
        value = new_values
        qs = self.queryset.filter(**{"%s__in" % key: value})
        pks = {str(getattr(o, key)) for o in qs}
        for val in value:
            if str(val) not in pks:
                raise ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                    params={"value": val},
                )
        return qs
