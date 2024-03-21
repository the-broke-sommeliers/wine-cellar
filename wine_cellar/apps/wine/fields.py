from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField


class OpenMultipleChoiceField(ModelMultipleChoiceField):
    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages["required"], code="required")
