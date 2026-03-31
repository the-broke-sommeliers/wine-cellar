import base64
import json

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
from wine_cellar.apps.wine.utils import lat_long_to_geojson


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

        vintage = ai_json.get("vintage")
        if isinstance(vintage, int) and 1900 <= vintage <= 2100:
            initial["vintage"] = vintage

        try:
            abv = float(ai_json.get("abs"))
            if 0 <= abv <= 100:
                initial["abv"] = abv
        except (TypeError, ValueError):
            pass

        alpha2 = ai_json.get("country")
        if alpha2:
            country = pycountry.countries.get(alpha_2=alpha2)
            if country:
                initial["country"] = country.alpha_2

        ai_type = (ai_json.get("type") or "").strip().lower()
        for val, label in WineType.choices:
            if label.lower() == ai_type:
                initial["wine_type"] = val
                break

        ai_sweetness = (ai_json.get("sweetness") or "").strip().lower()
        for value, label in Category.choices:
            if label.lower() == ai_sweetness:
                initial["category"] = value
                break

        for field, cfg in self.FIELD_CONFIG.items():
            value = ai_json.get(field)
            initial[field] = self.serialize_relation(
                value=value, model=cfg["model"], multi=cfg["multi"]
            )

        size_val = ai_json.get("size")
        if size_val:
            size_obj = Size.objects.filter(name=size_val).only("id").first()
            if size_obj:
                initial["size"] = size_obj.id

        if ai_json.get("location"):
            point = lat_long_to_geojson(ai_json["location"])
            if point:
                initial["location"] = point

        return base64.urlsafe_b64encode(
            json.dumps(initial, separators=(",", ":")).encode()
        ).decode()

    def deserialize_ai_payload(self, b64_initial):
        initial = json.loads(base64.urlsafe_b64decode(b64_initial).decode())
        for field, cfg in self.FIELD_CONFIG.items():
            initial[field] = self.deserialize_relation(
                initial.get(field),
                cfg["model"],
                cfg["multi"],
            )

        size_val = initial.get("size")
        if isinstance(size_val, int):
            initial["size"] = Size.objects.filter(pk=size_val).first()

        return initial
