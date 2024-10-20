from pathlib import Path

import pytest
from django.conf import settings
from django.templatetags.static import static


@pytest.mark.django_db
def test_wine_model(user, wine_factory, grape_factory):
    grape = grape_factory(name="Merlot")
    wine = wine_factory(user=user, grapes=[grape])
    assert wine.get_grapes == grape.name
    assert wine.image == static("images/bottle.svg")


@pytest.mark.django_db
def test_vineyard_model(vineyard):
    assert vineyard.name == str(vineyard)


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
