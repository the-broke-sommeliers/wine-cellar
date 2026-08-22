from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import caches
from PIL import ExifTags, Image

if TYPE_CHECKING:
    from wine_cellar.apps.wine.models import Wine

_DASH_CHARS = "‐‑‒–—―−"  # hyphen..horizontal bar, minus sign
_DASH_TRANSLATION = str.maketrans({c: "-" for c in _DASH_CHARS})

wine_prefill_cache = caches["wine_prefill"]
WINE_PREFILL_TIMEOUT = 6 * 60 * 60  # seconds


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "user_{0}/{1}".format(instance.user.pk, filename)


def make_thumbnail(instance, height=225):
    """
    Creates a proportional thumbnail with given height.
    Returns the path to the thumbnail file.
    """
    image_path = instance.image.name
    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
    img = Image.open(full_path)

    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == "Orientation":
                break
        exif = img._getexif()
        if exif:
            orientation_value = exif.get(orientation)
            if orientation_value == 3:
                img = img.rotate(180, expand=True)
            elif orientation_value == 6:
                img = img.rotate(270, expand=True)
            elif orientation_value == 8:
                img = img.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        # Image has no EXIF or orientation info
        pass

    aspect = img.width / img.height
    width = int(height * aspect)

    img.thumbnail((width, height), Image.LANCZOS)
    base, ext = os.path.splitext(image_path)
    name = f"{base}_thumb{ext}"
    thumb_full_path = os.path.join(settings.MEDIA_ROOT, name)

    img.save(thumb_full_path, format=img.format, quality=100)
    return name


def wine_to_json(wine: Wine) -> dict:
    if not wine:
        return None
    feature = {
        "name": wine.name,
        "country": wine.country,
        "country_name": wine.country_name,
        "country_icon": wine.country_icon,
        "image": wine.image_thumbnail,
        "vintage": wine.latest_vintage.year if wine.latest_vintage else None,
        "location": wine.location,
        "url": wine.get_absolute_url(),
    }
    return feature


def get_map_attributes(
    wines: list[Wine] = None, point: str = None, height: str = ""
) -> dict:
    map_settings = {
        "attribution": '<a href="https://openfreemap.org" target="_blank">'
        + 'OpenFreeMap</a> <a href="https://www.openmaptiles.org/" '
        + 'target="_blank">© OpenMapTiles</a> Data from '
        + '<a href="https://www.openstreetmap.org/copyright" '
        + 'target="_blank">OpenStreetMap</a>',
        "baseUrl": settings.MAP_BASEURL,
    }
    if point:
        map_settings["point"] = point
    if height:
        map_settings["style"] = {"height": height}

    attributes = {"map": map_settings}
    if wines is not None:
        wines = [wine_to_json(w) for w in wines]
        attributes["wines"] = wines
    return attributes


def match_choice_label(value, choices):
    """Case-insensitive match of `value` against a Django choices list's
    labels. Returns the matching value, or None if nothing matches."""
    value = (value or "").strip().lower()
    for val, label in choices:
        if label.lower() == value:
            return val
    return None


def lat_long_to_geojson(lat_long: str) -> dict:
    lat_str, long_str = lat_long.translate(_DASH_TRANSLATION).split(",")
    lat = float(lat_str.strip())
    long = float(long_str.strip())

    if not (-90 <= lat <= 90) or not (-180 <= long <= 180):
        raise ValueError(f"Coordinates out of range: lat={lat}, long={long}")

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [long, lat]},
    }
