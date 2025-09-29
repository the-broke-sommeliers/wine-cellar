import shutil
from pathlib import Path

import pytest
from django.conf import settings
from pytest_factoryboy import register

from wine_cellar.apps.storage.tests.factories import StorageFactory
from wine_cellar.apps.user.tests.factories import UserFactory
from wine_cellar.apps.wine.tests.factories import (
    ClassificationFactory,
    FoodPairingFactory,
    GrapeFactory,
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
register(ClassificationFactory)
register(SizeFactory)
register(SourceFactory)
register(StorageFactory)


@pytest.fixture
def clear_image_folder():
    yield
    path = settings.BASE_DIR / Path("test_media")
    shutil.rmtree(path)
