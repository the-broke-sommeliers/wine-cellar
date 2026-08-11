import io
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from PIL.JpegImagePlugin import JpegImageFile

from wine_cellar.apps.wine.utils import (
    get_map_attributes,
    lat_long_to_geojson,
    wine_to_json,
)


def _half_split_jpeg(orientation=None):
    """A 40x20 landscape JPEG, left half red / right half blue - a simple,
    JPEG-quality=100-safe way to detect rotation direction: dimensions swap
    for a 90-degree rotation, and the red/blue split moves to a different
    edge for each orientation value."""
    img = Image.new("RGB", (40, 20), color=(0, 0, 255))
    for x in range(20):
        for y in range(20):
            img.putpixel((x, y), (255, 0, 0))
    buf = io.BytesIO()
    if orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = orientation  # Orientation tag
        img.save(buf, format="JPEG", exif=exif.tobytes(), quality=100)
    else:
        img.save(buf, format="JPEG", quality=100)
    return buf.getvalue()


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


@pytest.mark.django_db
def test_make_thumbnail_no_exif_falls_back(
    clear_image_folder, user, wine_factory, wine_image_factory
):
    """No EXIF at all - the plain fallback path, made explicit rather than
    only exercised incidentally by other tests via the factory's default
    (EXIF-less) image."""
    wine = wine_factory(user=user)
    wine_image = wine_image_factory(
        user=user,
        wine=wine,
        image=SimpleUploadedFile(
            "no_exif.jpg", _half_split_jpeg(), content_type="image/jpeg"
        ),
    )
    thumb = Image.open(wine_image.thumbnail.path)
    assert thumb.size == (40, 20)
    assert thumb.getpixel((2, 2)) == (254, 0, 0)  # still red on the left
    assert thumb.getpixel((37, 2)) == (0, 0, 254)  # still blue on the right


@pytest.mark.django_db
def test_make_thumbnail_corrupt_exif_falls_back(
    clear_image_folder, user, wine_factory, wine_image_factory
):
    """A real-world quirk (truncated file, unsupported backend, ...) can
    make `Image._getexif()` itself raise - the `except (AttributeError,
    KeyError, IndexError)` guard must still produce an un-rotated
    thumbnail instead of propagating the error to the caller."""
    wine = wine_factory(user=user)
    with patch.object(JpegImageFile, "_getexif", side_effect=AttributeError):
        wine_image = wine_image_factory(
            user=user,
            wine=wine,
            image=SimpleUploadedFile(
                "corrupt_exif.jpg", _half_split_jpeg(), content_type="image/jpeg"
            ),
        )
    thumb = Image.open(wine_image.thumbnail.path)
    assert thumb.size == (40, 20)
    assert thumb.getpixel((2, 2)) == (254, 0, 0)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "orientation,expected_size,top_left,top_right,bottom_left,bottom_right",
    [
        # 180 degrees: no dimension swap, red/blue split flips left<->right.
        (3, (40, 20), (0, 0, 254), (254, 0, 0), (0, 0, 254), (254, 0, 0)),
        # 90 clockwise (rotate(270)): dimensions swap, red ends up on top.
        (6, (20, 40), (254, 0, 0), (254, 0, 0), (0, 0, 254), (0, 0, 254)),
        # 90 counter-clockwise (rotate(90)): dimensions swap, blue on top.
        (8, (20, 40), (0, 0, 254), (0, 0, 254), (254, 0, 0), (254, 0, 0)),
    ],
)
def test_make_thumbnail_rotates_by_exif_orientation(
    clear_image_folder,
    user,
    wine_factory,
    wine_image_factory,
    orientation,
    expected_size,
    top_left,
    top_right,
    bottom_left,
    bottom_right,
):
    """Phone photos routinely carry an EXIF orientation tag - the thumbnail
    must be rotated to match, not saved sideways/upside-down."""
    wine = wine_factory(user=user)
    wine_image = wine_image_factory(
        user=user,
        wine=wine,
        image=SimpleUploadedFile(
            f"exif_{orientation}.jpg",
            _half_split_jpeg(orientation),
            content_type="image/jpeg",
        ),
    )
    thumb = Image.open(wine_image.thumbnail.path)
    assert thumb.size == expected_size
    w, h = thumb.size
    assert thumb.getpixel((2, 2)) == top_left
    assert thumb.getpixel((w - 3, 2)) == top_right
    assert thumb.getpixel((2, h - 3)) == bottom_left
    assert thumb.getpixel((w - 3, h - 3)) == bottom_right
