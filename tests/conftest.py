import json
import shutil
from pathlib import Path

import pytest
from django.conf import settings
from pytest_factoryboy import register

from wine_cellar.apps.storage.tests.factories import StorageFactory, StorageItemFactory
from wine_cellar.apps.user.tests.factories import UserFactory
from wine_cellar.apps.wine.tests.factories import (
    AppellationFactory,
    AttributeFactory,
    FoodPairingFactory,
    GrapeFactory,
    RegionFactory,
    SizeFactory,
    SourceFactory,
    VineyardFactory,
    WineFactory,
    WineImageFactory,
)

register(UserFactory)
register(WineFactory)
register(GrapeFactory)
register(WineImageFactory)
register(VineyardFactory)
register(FoodPairingFactory)
register(AttributeFactory)
register(SizeFactory)
register(SourceFactory)
register(StorageFactory)
register(StorageItemFactory)
register(RegionFactory)
register(AppellationFactory)


@pytest.fixture
def clear_image_folder():
    yield
    path = settings.BASE_DIR / Path("test_media")
    shutil.rmtree(path)


@pytest.fixture
def geojson_point():
    return json.dumps(
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [90.0, 45.0]}}
    )
