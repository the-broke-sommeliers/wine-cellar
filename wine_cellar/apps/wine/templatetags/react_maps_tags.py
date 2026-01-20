import json

from django import template
from django.utils.html import format_html

from wine_cellar.apps.wine.models import Wine
from wine_cellar.apps.wine.utils import get_map_attributes

register = template.Library()


@register.simple_tag()
def react_detail_map(wine: Wine):
    attributes = get_map_attributes([wine], height="30vh")
    return format_html(
        '<div id="wine_map" ' 'data-attributes="{attributes}"></div>',
        attributes=json.dumps(attributes),
    )


@register.simple_tag()
def react_map(wines: list[Wine]):
    attributes = get_map_attributes(wines)
    return format_html(
        '<div id="wine_map" ' 'data-attributes="{attributes}"></div>',
        attributes=json.dumps(attributes),
    )


@register.simple_tag()
def react_choose_point(polygon, point, name):
    attributes = get_map_attributes(point)
    return format_html(
        '<div id="map_select_point" data-attributes="{attributes}"></div>',
        attributes=json.dumps(attributes),
    )
