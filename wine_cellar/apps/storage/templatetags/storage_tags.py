import json

from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag()
def storage_cells(storages):
    return format_html(
        '<div id="storage-data" ' 'data-attributes="{attributes}"></div>',
        attributes=json.dumps(storages),
    )
