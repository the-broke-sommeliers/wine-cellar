import pytest
from django.conf import settings

from wine_cellar.apps.wine.utils import (
    get_map_attributes,
    wine_to_json,
)


@pytest.mark.django_db
def test_wine_to_json_none(wine_factory, geojson_point):
    wine = wine_factory(name="Test Wine", location=geojson_point)
    expected = {
        "name": "Test Wine",
        "country": "DE",
        "country_name": "Germany",
        "country_icon": "🇩🇪",
        "image": wine.image_thumbnail,
        "vintage": wine.vintage,
        "location": geojson_point,
        "url": wine.get_absolute_url(),
    }
    assert wine_to_json(wine) == expected


@pytest.mark.django_db
def test_get_map_attributes(wine_factory):
    expected = {
        "map": {
            "attribution": '<a href="https://openfreemap.org" target="_blank">'
            + 'OpenFreeMap</a> <a href="https://www.openmaptiles.org/" '
            + 'target="_blank">© OpenMapTiles</a> Data from '
            + '<a href="https://www.openstreetmap.org/copyright" '
            + 'target="_blank">OpenStreetMap</a>',
            "baseUrl": settings.MAP_BASEURL,
        }
    }
    assert get_map_attributes() == expected


@pytest.mark.django_db
def test_get_map_attributes_with_wine(wine_factory, geojson_point):
    wine = wine_factory(name="Test Wine", location=geojson_point)
    expected = {
        "map": {
            "attribution": '<a href="https://openfreemap.org" target="_blank">'
            + 'OpenFreeMap</a> <a href="https://www.openmaptiles.org/" '
            + 'target="_blank">© OpenMapTiles</a> Data from '
            + '<a href="https://www.openstreetmap.org/copyright" '
            + 'target="_blank">OpenStreetMap</a>',
            "baseUrl": settings.MAP_BASEURL,
        },
        "wines": [
            {
                "name": "Test Wine",
                "country": "DE",
                "country_name": "Germany",
                "country_icon": "🇩🇪",
                "image": wine.image_thumbnail,
                "vintage": wine.vintage,
                "location": geojson_point,
                "url": wine.get_absolute_url(),
            }
        ],
    }
    assert get_map_attributes([wine]) == expected


@pytest.mark.django_db
def test_get_map_attributes_with_point_height(geojson_point):
    expected = {
        "map": {
            "attribution": '<a href="https://openfreemap.org" target="_blank">'
            + 'OpenFreeMap</a> <a href="https://www.openmaptiles.org/" '
            + 'target="_blank">© OpenMapTiles</a> Data from '
            + '<a href="https://www.openstreetmap.org/copyright" '
            + 'target="_blank">OpenStreetMap</a>',
            "baseUrl": settings.MAP_BASEURL,
            "point": geojson_point,
            "style": {"height": "50vh"},
        },
    }
    assert get_map_attributes(point=geojson_point, height="50vh") == expected
