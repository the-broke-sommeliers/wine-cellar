import shutil
from pathlib import Path

import pytest
from django.conf import settings
from pytest_factoryboy import register

from wine_cellar.apps.wine.tests.factories import (
    ClassificationFactory,
    FoodPairingFactory,
    GrapeFactory,
    RegionFactory,
    UserFactory,
    WineFactory,
    WineImageFactory,
    WineryFactory,
)

register(UserFactory)
register(RegionFactory)
register(WineFactory)
register(GrapeFactory)
register(WineImageFactory)
register(WineryFactory)
register(FoodPairingFactory)
register(ClassificationFactory)


@pytest.fixture
def clear_image_folder():
    yield
    path = settings.BASE_DIR / Path("test_media")
    shutil.rmtree(path)
