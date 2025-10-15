import json

from django import template
from django.conf import settings
from django.utils.html import format_html

from wine_cellar.apps.wine.models import Wine

register = template.Library()


def wine_to_json(wine: Wine):
    feature = {
        "name": wine.name,
        "country": wine.country,
        "country_name": wine.country_name,
        "country_icon": wine.country_icon,
        "image": wine.image_thumbnail,
        "vintage": wine.vintage,
        "url": wine.get_absolute_url(),
    }
    return feature


@register.simple_tag()
def react_map(wines):
    map_settings = {
        "attribution": '<a href="https://openfreemap.org" target="_blank">'
        + 'OpenFreeMap</a> <a href="https://www.openmaptiles.org/" '
        + 'target="_blank">© OpenMapTiles</a> Data from '
        + '<a href="https://www.openstreetmap.org/copyright" '
        + 'target="_blank">OpenStreetMap</a>',
        "baseUrl": settings.MAP_BASEURL,
    }
    wines = [wine_to_json(w) for w in wines]
    attributes = {"map": map_settings, "wines": wines}

    return format_html(
        '<div id="wine_map" ' 'data-attributes="{attributes}"></div>',
        attributes=json.dumps(attributes),
    )
