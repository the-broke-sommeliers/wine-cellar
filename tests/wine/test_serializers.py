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

    initial = serializer.serialize_ai_payload(ai_json)

    assert initial["name"] == "Reserva 2018"
    assert initial["region"] == region.pk
    assert initial["size"] == Size.objects.filter(name=0.75).first().pk
    assert initial["abv"] == 14.5


@pytest.mark.django_db
def test_deserialize_ai_payload_returns_model_instances(region_factory):
    serializer = WineAiSerializer()
    region = region_factory(name="Mosel")

    payload = {"name": "Riesling", "region": region.pk}

    result = serializer.deserialize_ai_payload(payload)

    assert result["name"] == "Riesling"
    assert result["region"] == region
    assert isinstance(result["region"], Region)


@pytest.mark.django_db
def test_deserialize_ai_payload_leaves_absent_relations_untouched():
    """A payload with no relation fields (e.g. a plain barcode prefill) should
    not have `region`/`appellation`/`grapes`/`vineyard` invented as None/[]."""
    serializer = WineAiSerializer()

    result = serializer.deserialize_ai_payload({"barcode": "12345"})

    assert result == {"barcode": "12345"}


@pytest.mark.django_db
def test_deserialize_ai_payload_does_not_mutate_input():
    serializer = WineAiSerializer()
    payload = {"name": "Riesling", "grapes": [{"new": "Riesling"}]}

    serializer.deserialize_ai_payload(payload)

    assert payload["grapes"] == [{"new": "Riesling"}]


@pytest.mark.django_db
def test_invalid_alcohol_string_is_ignored():
    serializer = WineAiSerializer()
    ai_json = {"name": "Bad Data Wine", "abs": "Unknown %"}

    initial = serializer.serialize_ai_payload(ai_json)

    assert "abv" not in initial


@pytest.mark.django_db
def test_serialize_relation_raises_type_error_on_invalid_multi():
    serializer = WineAiSerializer()

    with pytest.raises(TypeError):
        serializer.serialize_relation(["Region 1", "Region 2"], Region, multi=False)


@pytest.mark.django_db
def test_serialize_ai_payload_wine_type_mapped():
    serializer = WineAiSerializer()
    ai_json = {"name": "Rouge", "type": "red"}
    initial = serializer.serialize_ai_payload(ai_json)
    assert initial["wine_type"] == "RE"


@pytest.mark.django_db
def test_serialize_ai_payload_category_mapped():
    serializer = WineAiSerializer()
    ai_json = {"name": "Dry Red", "sweetness": "dry"}
    initial = serializer.serialize_ai_payload(ai_json)
    assert initial["category"] == "DR"


@pytest.mark.django_db
def test_serialize_ai_payload_missing_size_skips():
    serializer = WineAiSerializer()
    ai_json = {"name": "Wine", "size": 99.99}
    initial = serializer.serialize_ai_payload(ai_json)
    assert "size" not in initial


@pytest.mark.django_db
def test_serialize_ai_payload_with_location():
    serializer = WineAiSerializer()
    ai_json = {"name": "Wine", "location": "48.1374, 11.5755"}
    initial = serializer.serialize_ai_payload(ai_json)
    assert initial["location"]["type"] == "Feature"
    assert initial["location"]["geometry"]["type"] == "Point"


@pytest.mark.django_db
def test_serialize_ai_payload_with_unicode_minus_location():
    serializer = WineAiSerializer()
    ai_json = {"name": "Wine", "location": "48.1374,−0.6603"}
    initial = serializer.serialize_ai_payload(ai_json)
    assert initial["location"]["geometry"]["coordinates"] == [-0.6603, 48.1374]


@pytest.mark.django_db
def test_serialize_ai_payload_with_invalid_location_dropped():
    serializer = WineAiSerializer()
    ai_json = {"name": "Wine", "location": "999,999"}
    initial = serializer.serialize_ai_payload(ai_json)
    assert "location" not in initial


@pytest.mark.django_db
def test_serialize_relation_unknown_region_returns_new(region_factory):
    serializer = WineAiSerializer()
    region_factory(name="Bordeaux")
    result = serializer.serialize_relation("Unknown Region", Region, multi=False)
    assert result == {"new": "Unknown Region"}


@pytest.mark.django_db
def test_deserialize_relation_none_multi_returns_empty():
    serializer = WineAiSerializer()
    result = serializer.deserialize_relation(None, Grape, multi=True)
    assert result == []


@pytest.mark.django_db
def test_deserialize_ai_payload_with_new_grape_value(grape_factory):
    serializer = WineAiSerializer()
    grape = grape_factory(name="Tempranillo")
    payload = {"name": "Rioja", "grapes": [grape.pk, {"new": "Garnacha"}]}
    result = serializer.deserialize_ai_payload(payload)
    assert grape in result["grapes"]
    assert "Garnacha" in result["grapes"]


@pytest.mark.django_db
def test_deserialize_ai_payload_resolves_size(size_factory):
    serializer = WineAiSerializer()
    size = size_factory(name=0.75)
    payload = {"name": "Wine", "size": size.pk}
    result = serializer.deserialize_ai_payload(payload)
    assert result["size"] == size
