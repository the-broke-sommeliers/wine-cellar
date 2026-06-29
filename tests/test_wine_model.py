import datetime
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


# ---------------------------------------------------------------------------
# Wine model property coverage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_type_label(user, wine_factory):
    wine = wine_factory(user=user, wine_type="RE")
    assert wine.get_type == "Red"


@pytest.mark.django_db
def test_get_category_label(user, wine_factory):
    wine = wine_factory(user=user, wine_type="WH")
    wine.category = "DR"
    wine.save()
    assert wine.get_category == "Dry"


@pytest.mark.django_db
def test_get_category_none(user, wine_factory):
    wine = wine_factory(user=user)
    wine.category = None
    wine.save()
    assert wine.get_category is None


@pytest.mark.django_db
def test_country_name(user, wine_factory):
    wine = wine_factory(user=user, country="DE")
    assert wine.country_name == "Germany"


@pytest.mark.django_db
def test_country_icon(user, wine_factory):
    wine = wine_factory(user=user, country="DE")
    assert wine.country_icon  # flag emoji, non-empty


@pytest.mark.django_db
def test_total_stock_excludes_deleted(user, wine_factory, storage_item_factory):
    wine = wine_factory(user=user)
    storage = user.storage_set.first()
    storage_item_factory(wine=wine, storage=storage)
    storage_item_factory(wine=wine, storage=storage, deleted=True)
    assert wine.total_stock == 1


@pytest.mark.django_db
def test_get_stock_ordering(user, wine_factory, storage_factory, storage_item_factory):
    wine = wine_factory(user=user)
    storage = storage_factory(user=user, rows=3, columns=3)
    item_b = storage_item_factory(wine=wine, storage=storage, row=2, column=1)
    item_a = storage_item_factory(wine=wine, storage=storage, row=1, column=1)
    stock = list(wine.get_stock)
    assert stock[0] == item_a
    assert stock[1] == item_b


@pytest.mark.django_db
def test_get_food_pairings(user, wine_factory, food_pairing_factory):
    pairing1 = food_pairing_factory(name="Cheese")
    pairing2 = food_pairing_factory(name="Steak")
    wine = wine_factory(user=user)
    wine.food_pairings.set([pairing1, pairing2])
    result = wine.get_food_pairings
    assert "Cheese" in result
    assert "Steak" in result


@pytest.mark.django_db
def test_get_attributes(user, wine_factory, attribute_factory):
    attr1 = attribute_factory(name="Organic")
    attr2 = attribute_factory(name="Natural")
    wine = wine_factory(user=user)
    wine.attributes.set([attr1, attr2])
    result = wine.get_attributes
    assert "Organic" in result
    assert "Natural" in result


@pytest.mark.django_db
def test_get_vineyards(user, wine_factory, vineyard_factory):
    v1 = vineyard_factory(name="Estate A")
    v2 = vineyard_factory(name="Estate B")
    wine = wine_factory(user=user)
    wine.vineyard.set([v1, v2])
    result = wine.get_vineyards
    assert "Estate A" in result
    assert "Estate B" in result


@pytest.mark.django_db
def test_get_sources(user, wine_factory, source_factory):
    s1 = source_factory(name="Supermarket")
    s2 = source_factory(name="Winery Direct")
    wine = wine_factory(user=user)
    wine.source.set([s1, s2])
    result = wine.get_sources
    assert "Supermarket" in result
    assert "Winery Direct" in result


@pytest.mark.django_db
def test_get_price_with_currency(user, wine_factory):
    wine = wine_factory(user=user, price=Decimal("14.99"))
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    result = wine.get_price_with_currency
    assert "14" in result
    assert currency in result


@pytest.mark.django_db
def test_drink_by_warning_date(user, wine_factory):
    wine = wine_factory(user=user)
    expected = datetime.date.today() + datetime.timedelta(days=30)
    assert wine.drink_by_warning_date == expected


@pytest.mark.django_db
def test_grape_str_empty_name(grape_factory):
    grape = grape_factory(name="")
    assert str(grape) == ""
