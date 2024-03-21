from pathlib import Path

import pytest
from django.conf import settings
from django.templatetags.static import static

# from django.urls import reverse
# from pytest_django.asserts import assertURLEqual


@pytest.mark.django_db
def test_wine_model(user, wine_factory, grape_factory, vintage_factory):
    grape = grape_factory(name="Merlot")
    vintage = vintage_factory(name=2021)
    wine = wine_factory(user=user, grapes=[grape], vintage=[vintage])
    assert wine.get_grapes == grape.name
    assert wine.get_vintages == str(vintage.name)
    assert wine.image == static("images/red_glass2.svg")


@pytest.mark.django_db
def test_region_model(region):
    assert region.name == str(region)


@pytest.mark.django_db
def test_winery_model(winery):
    assert winery.name == str(winery)


@pytest.mark.django_db
def test_food_pairing_model(food_pairing):
    assert food_pairing.name == str(food_pairing)


@pytest.mark.django_db
def test_classification_model(classification):
    assert classification.name == str(classification)


@pytest.mark.django_db
def test_wine_image(clear_image_folder, user, wine_factory, wine_image_factory):
    wine = wine_factory(user=user)
    wine_image = wine_image_factory(user=user, wine=wine)
    assert wine.image == wine_image.image.url
    assert wine_image.image.path == str(
        settings.MEDIA_ROOT / Path("user_" + str(user.pk) + "/example.jpg")
    )
