from django import template

register = template.Library()


@register.filter
def add_error_attr(field, attrs):
    if hasattr(field, "errors") and field.errors:
        key, val = attrs.split(":")
        field.field.widget.attrs[key] = val
    return field
