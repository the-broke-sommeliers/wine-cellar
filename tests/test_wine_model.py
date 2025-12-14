from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.templatetags.static import static
from django.utils.formats import number_format

from wine_cellar.apps.user.models import UserSettings


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
def test_attribute_model(attribute):
    assert attribute.name == str(attribute)


@pytest.mark.django_db
def test_wine_image(clear_image_folder, user, wine_factory, wine_image_factory):
    wine = wine_factory(user=user)
    wine_image = wine_image_factory(user=user, wine=wine)
    assert wine.image == wine_image.image.url
    assert wine_image.image.path == str(
        settings.MEDIA_ROOT / Path("user_" + str(user.pk) + "/example.jpg")
    )


@pytest.mark.django_db
def test_get_average_price_with_currency(user, wine_factory, storage_item_factory):
    wine = wine_factory(user=user)
    storage_item_factory(wine=wine, price=10.00)
    storage_item_factory(wine=wine, price=20.00)

    avg = Decimal("15.00")
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    expected = f"{number_format(avg, use_l10n=True)}{currency}"

    assert wine.get_average_price_with_currency == expected


@pytest.mark.django_db
def test_get_average_price_no_items_returns_none(user, wine_factory):
    wine = wine_factory(user=user)
    assert wine.get_average_price_with_currency is None


@pytest.mark.django_db
def test_get_average_ignores_null_prices(user, wine_factory, storage_item_factory):
    wine = wine_factory(user=user)
    # create one item with null price and one with a price
    storage_item_factory(wine=wine)  # price is None by default
    storage_item_factory(wine=wine, price=Decimal("20.00"))

    avg = Decimal("20.00")
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    expected = f"{number_format(avg, use_l10n=True)}{currency}"
    assert wine.get_average_price_with_currency == expected


@pytest.mark.django_db
def test_get_average_all_null_prices_returns_none(
    user, wine_factory, storage_item_factory
):
    wine = wine_factory(user=user)
    storage_item_factory(wine=wine)
    storage_item_factory(wine=wine)
    assert wine.get_average_price_with_currency is None


@pytest.mark.django_db
def test_get_average_respects_user_currency(user, wine_factory, storage_item_factory):
    wine = wine_factory(user=user)
    storage_item_factory(wine=wine, price=Decimal("10.00"))
    storage_item_factory(wine=wine, price=Decimal("20.00"))

    # set user preference to USD
    us = UserSettings.objects.create(user=user, currency="USD")
    avg = Decimal("15.00")
    currency = settings.CURRENCY_SYMBOLS.get(us.currency)
    expected = f"{number_format(avg, use_l10n=True)}{currency}"
    assert wine.get_average_price_with_currency == expected
