import shutil
from pathlib import Path

import pytest
from django.conf import settings
from pytest_factoryboy import register

from wine_cellar.apps.wine.tests.factories import (
    ClassificationFactory,
    FoodPairingFactory,
    GrapeFactory,
    SizeFactory,
    SourceFactory,
    UserFactory,
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


@pytest.fixture
def clear_image_folder():
    yield
    path = settings.BASE_DIR / Path("test_media")
    shutil.rmtree(path)
