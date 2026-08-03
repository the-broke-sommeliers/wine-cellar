import pytest
from django.conf import settings

from wine_cellar.apps.wine.utils import (
    get_map_attributes,
    lat_long_to_geojson,
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


def test_latlong_to_point(geojson_point_dict):
    long = geojson_point_dict["geometry"]["coordinates"][0]
    lat = geojson_point_dict["geometry"]["coordinates"][1]
    assert lat_long_to_geojson(str(lat) + "," + str(long)) == geojson_point_dict


def test_latlong_to_point_unicode_minus_sign():
    result = lat_long_to_geojson("48.1374,−0.6603")
    assert result["geometry"]["coordinates"] == [-0.6603, 48.1374]


@pytest.mark.parametrize(
    "dash_char",
    ["‐", "‑", "‒", "–", "—", "―", "−"],
)
def test_latlong_to_point_dash_variants(dash_char):
    result = lat_long_to_geojson(f"48.1374,{dash_char}0.6603")
    assert result["geometry"]["coordinates"] == [-0.6603, 48.1374]


def test_latlong_to_point_lat_out_of_range_raises():
    with pytest.raises(ValueError):
        lat_long_to_geojson("120,10")


def test_latlong_to_point_long_out_of_range_raises():
    with pytest.raises(ValueError):
        lat_long_to_geojson("45,200")


def test_latlong_to_point_malformed_raises_value_error():
    with pytest.raises(ValueError):
        lat_long_to_geojson("not,numbers")


def test_wine_to_json_none_returns_none():
    assert wine_to_json(None) is None
