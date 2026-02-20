import base64
import json

import pytest

from wine_cellar.apps.wine.models import Grape, Region, Size
from wine_cellar.apps.wine.serializers import WineAiSerializer


@pytest.mark.django_db
def test_serialize_relation_finds_existing_db_objects(grape_factory):
    serializer = WineAiSerializer()
    existing_grape = grape_factory(name="Nebbiolo")

    input_data = ["Nebbiolo", "Unknown Grape"]
    result = serializer.serialize_relation(input_data, Grape, multi=True)

    assert result == [existing_grape.pk, {"new": "Unknown Grape"}]


@pytest.mark.django_db
def test_serialize_ai_payload_full_cycle(region_factory, size_factory):
    serializer = WineAiSerializer()
    region = region_factory(name="Rioja")

    ai_json = {
        "name": "Reserva 2018",
        "vintage": 2018,
        "abs": 14.5,
        "country": "ES",
        "region": "Rioja",
        "size": 0.75,
    }

    b64_result = serializer.serialize_ai_payload(ai_json)

    decoded_json = json.loads(base64.urlsafe_b64decode(b64_result).decode())

    assert decoded_json["name"] == "Reserva 2018"
    assert decoded_json["region"] == region.pk
    assert decoded_json["size"] == Size.objects.filter(name=0.75).first().pk
    assert decoded_json["abv"] == 14.5


@pytest.mark.django_db
def test_deserialize_ai_payload_returns_model_instances(region_factory):
    serializer = WineAiSerializer()
    region = region_factory(name="Mosel")

    payload = {"name": "Riesling", "region": region.pk}
    b64_input = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    result = serializer.deserialize_ai_payload(b64_input)

    assert result["name"] == "Riesling"
    assert result["region"] == region
    assert isinstance(result["region"], Region)


@pytest.mark.django_db
def test_invalid_alcohol_string_is_ignored():
    serializer = WineAiSerializer()
    ai_json = {"name": "Bad Data Wine", "abs": "Unknown %"}

    b64_result = serializer.serialize_ai_payload(ai_json)
    decoded = json.loads(base64.urlsafe_b64decode(b64_result).decode())

    assert "abv" not in decoded


@pytest.mark.django_db
def test_serialize_relation_raises_type_error_on_invalid_multi():
    serializer = WineAiSerializer()

    with pytest.raises(TypeError):
        serializer.serialize_relation(["Region 1", "Region 2"], Region, multi=False)
