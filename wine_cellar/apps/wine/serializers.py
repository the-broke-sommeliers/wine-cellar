import re

import pycountry

from wine_cellar.apps.wine.models import (
    Appellation,
    Category,
    Grape,
    Region,
    Size,
    Vineyard,
    WineType,
)
from wine_cellar.apps.wine.utils import lat_long_to_geojson, match_choice_label

_SIZE_UNITS_TO_LITERS = {"ml": 0.001, "cl": 0.01, "l": 1.0}
_SIZE_RE = re.compile(r"^\s*([\d.]+)\s*(ml|cl|l)?\s*$", re.IGNORECASE)


def _normalize_size_liters(value):
    """Coerce an AI-reported bottle size to liters. Accepts a bare number
    (assumed already liters, unless implausibly large for a bottle - then
    it's assumed to be mL) or a string with an ml/cl/l suffix."""
    if isinstance(value, (int, float)):
        number, unit = value, None
    elif isinstance(value, str):
        match = _SIZE_RE.match(value)
        if not match:
            return None
        try:
            number = float(match.group(1))
        except ValueError:
            return None
        unit = match.group(2)
    else:
        return None

    liters = number * _SIZE_UNITS_TO_LITERS[unit.lower()] if unit else number
    # A real bottle is never >10L - an unsuffixed number that large is mL.
    if not unit and liters > 10:
        liters /= 1000
    return round(liters, 2)


class WineAiSerializer:

    FIELD_CONFIG = {
        "grapes": {"model": Grape, "multi": True},
        "vineyard": {"model": Vineyard, "multi": True},
        "region": {"model": Region, "multi": False},
        "appellation": {"model": Appellation, "multi": False},
    }

    def serialize_relation(self, value, model, multi=False):
        if multi:
            if value is None:
                value = []
            elif not isinstance(value, (list, tuple)):
                value = [value]
        else:
            if isinstance(value, (list, tuple)):
                raise TypeError(
                    f"Expected single value for multi=False, got {type(value)}"
                )

        values = value if multi else [value]
        objs = model.objects.filter(name__in=values).only("pk", "name")
        lookup = {o.name: o.pk for o in objs}

        result = []
        for v in values:
            result.append(lookup.get(v, {"new": v}))

        return result if multi else result[0]

    def deserialize_relation(self, value, model, multi=False):
        if multi:
            if value is None:
                value = []
            elif not isinstance(value, (list, tuple)):
                value = [value]
        else:
            if isinstance(value, (list, tuple)):
                raise TypeError(
                    f"Expected single value for multi=False, got {type(value)}"
                )

        values = value if multi else [value]
        pks = [v for v in values if isinstance(v, int)]
        objs = {o.pk: o for o in model.objects.filter(pk__in=pks)}

        result = []
        for v in values:
            if isinstance(v, int) and v in objs:
                result.append(objs[v])
            elif isinstance(v, dict) and "new" in v:
                result.append(v["new"])

        return result if multi else (result[0] if result else None)

    def serialize_ai_payload(self, ai_json):
        initial = {}

        if ai_json.get("name"):
            initial["name"] = ai_json["name"]

        try:
            vintage = int(ai_json.get("vintage"))
            if 1900 <= vintage <= 2100:
                initial["vintage"] = vintage
        except (TypeError, ValueError):
            pass

        abv_raw = ai_json.get("abs")
        if isinstance(abv_raw, str):
            abv_raw = abv_raw.strip().rstrip("%")
        try:
            abv = float(abv_raw)
            if 0 <= abv <= 100:
                initial["abv"] = abv
        except (TypeError, ValueError):
            pass

        alpha2 = ai_json.get("country")
        if alpha2:
            country = pycountry.countries.get(alpha_2=alpha2)
            if country:
                initial["country"] = country.alpha_2

        if wine_type := match_choice_label(ai_json.get("type"), WineType.choices):
            initial["wine_type"] = wine_type

        if category := match_choice_label(ai_json.get("sweetness"), Category.choices):
            initial["category"] = category

        for field, cfg in self.FIELD_CONFIG.items():
            value = ai_json.get(field)
            initial[field] = self.serialize_relation(
                value=value, model=cfg["model"], multi=cfg["multi"]
            )

        size_val = _normalize_size_liters(ai_json.get("size"))
        if size_val:
            size_obj = Size.objects.filter(name=size_val).only("id").first()
            if size_obj:
                initial["size"] = size_obj.id

        if ai_json.get("location"):
            try:
                initial["location"] = lat_long_to_geojson(ai_json["location"])
            except (TypeError, ValueError):
                pass

        return initial

    def deserialize_ai_payload(self, initial):
        initial = dict(initial)
        for field, cfg in self.FIELD_CONFIG.items():
            if field not in initial:
                continue
            initial[field] = self.deserialize_relation(
                initial[field],
                cfg["model"],
                cfg["multi"],
            )

        size_val = initial.get("size")
        if isinstance(size_val, int):
            initial["size"] = Size.objects.filter(pk=size_val).first()

        return initial
