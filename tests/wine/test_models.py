import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.db.models import FETCH_RAISE
from django.db.models.signals import post_save
from django.templatetags.static import static
from django.utils.formats import number_format

from wine_cellar.apps.user.models import UserSettings
from wine_cellar.apps.wine.models import ImageType, WineImage
from wine_cellar.apps.wine.signals import generate_thumbnail


@pytest.mark.django_db
def test_wine_model(user, wine_factory, grape_factory, django_assert_num_queries):
    grape = grape_factory(name="Merlot")
    wine = wine_factory(user=user, grapes=[grape])
    with django_assert_num_queries(1):
        assert wine.get_grapes == grape.name
    # 1 query for latest_vintage, 1 for that vintage's image lookup.
    with django_assert_num_queries(2):
        assert wine.image == static("images/bottle.svg")


@pytest.mark.django_db
def test_wine_image_thumbnail_falls_back_to_full_image_when_no_thumbnail(
    clear_image_folder,
    user,
    wine_factory,
    wine_image_factory,
    django_assert_num_queries,
):
    """`generate_thumbnail` normally fills `thumbnail` on every save - to
    observe the pre-signal/signal-skipped fallback, create the front image
    with the signal disconnected."""
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    post_save.disconnect(generate_thumbnail, sender=WineImage)
    try:
        front = wine_image_factory(
            user=user, vintage=vintage, image_type=ImageType.FRONT
        )
    finally:
        post_save.connect(generate_thumbnail, sender=WineImage)
    assert not front.thumbnail
    # latest_vintage is already cached from the fetch above - only the
    # vintage's own image lookup remains.
    with django_assert_num_queries(1):
        assert wine.image_thumbnail == front.image.url


@pytest.mark.django_db
def test_wine_image_thumbnails_returns_ordered_by_type(
    clear_image_folder,
    user,
    wine_factory,
    wine_image_factory,
    django_assert_num_queries,
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    # Created out of order, and skipping LABEL_FRONT entirely.
    label_back = wine_image_factory(
        user=user, vintage=vintage, image_type=ImageType.LABEL_BACK
    )
    front = wine_image_factory(user=user, vintage=vintage, image_type=ImageType.FRONT)
    back = wine_image_factory(user=user, vintage=vintage, image_type=ImageType.BACK)
    front.refresh_from_db()
    back.refresh_from_db()
    label_back.refresh_from_db()
    # latest_vintage is already cached from the fetch above - only the
    # vintage's own image lookup remains.
    with django_assert_num_queries(1):
        assert wine.image_thumbnails == [
            front.thumbnail.url,
            back.thumbnail.url,
            label_back.thumbnail.url,
        ]


@pytest.mark.django_db
def test_vineyard_model(vineyard, django_assert_num_queries):
    with django_assert_num_queries(0):
        assert vineyard.name == str(vineyard)


@pytest.mark.django_db
def test_food_pairing_model(food_pairing, django_assert_num_queries):
    with django_assert_num_queries(0):
        assert food_pairing.name == str(food_pairing)


@pytest.mark.django_db
def test_attribute_model(attribute, django_assert_num_queries):
    with django_assert_num_queries(0):
        assert attribute.name == str(attribute)


@pytest.mark.django_db
def test_wine_image(
    clear_image_folder,
    user,
    wine_factory,
    wine_image_factory,
    django_assert_num_queries,
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    wine_image = wine_image_factory(user=user, vintage=vintage)
    # latest_vintage is already cached from the fetch above - only the
    # vintage's own image lookup remains.
    with django_assert_num_queries(1):
        assert wine.image == wine_image.image.url
    assert wine_image.image.path == str(
        settings.MEDIA_ROOT / Path("user_" + str(user.pk) + "/example.jpg")
    )


@pytest.mark.django_db
def test_get_average_price_with_currency(
    user, wine_factory, storage_item_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    storage_item_factory(vintage=vintage, price=10.00)
    storage_item_factory(vintage=vintage, price=20.00)

    avg = Decimal("15.00")
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    expected = f"{number_format(avg, use_l10n=True)}{currency}"

    with django_assert_num_queries(3):
        assert vintage.get_average_price_with_currency == expected


@pytest.mark.django_db
def test_get_average_price_no_items_returns_none(
    user, wine_factory, django_assert_num_queries
):
    vintage = wine_factory(user=user).latest_vintage
    with django_assert_num_queries(3):
        assert vintage.get_average_price_with_currency is None


@pytest.mark.django_db
def test_get_average_ignores_null_prices(
    user, wine_factory, storage_item_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    # create one item with null price and one with a price
    storage_item_factory(vintage=vintage)  # price is None by default
    storage_item_factory(vintage=vintage, price=Decimal("20.00"))

    avg = Decimal("20.00")
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    expected = f"{number_format(avg, use_l10n=True)}{currency}"
    with django_assert_num_queries(3):
        assert vintage.get_average_price_with_currency == expected


@pytest.mark.django_db
def test_get_average_all_null_prices_returns_none(
    user, wine_factory, storage_item_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    storage_item_factory(vintage=vintage)
    storage_item_factory(vintage=vintage)
    with django_assert_num_queries(3):
        assert vintage.get_average_price_with_currency is None


@pytest.mark.django_db
def test_get_average_respects_user_currency(
    user, wine_factory, storage_item_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    storage_item_factory(vintage=vintage, price=Decimal("10.00"))
    storage_item_factory(vintage=vintage, price=Decimal("20.00"))

    # set user preference to USD
    us = UserSettings.objects.create(user=user, currency="USD")
    avg = Decimal("15.00")
    currency = settings.CURRENCY_SYMBOLS.get(us.currency)
    expected = f"{number_format(avg, use_l10n=True)}{currency}"
    with django_assert_num_queries(3):
        assert vintage.get_average_price_with_currency == expected


@pytest.mark.django_db
def test_get_average_price_includes_vintage_reference_price(
    user, wine_factory, storage_item_factory, django_assert_num_queries
):
    """The vintage's own reference price counts as a known price alongside
    what was actually paid for stocked bottles - not restricted to stock."""
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    vintage.price = Decimal("30.00")
    vintage.save()
    storage_item_factory(vintage=vintage, price=Decimal("10.00"))
    storage_item_factory(vintage=vintage, price=Decimal("20.00"))

    avg = Decimal("20.00")  # (30 + 10 + 20) / 3
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    expected = f"{number_format(avg, use_l10n=True)}{currency}"
    with django_assert_num_queries(3):
        assert vintage.get_average_price_with_currency == expected


@pytest.mark.django_db
def test_get_average_price_from_reference_price_with_no_stock(
    user, wine_factory, django_assert_num_queries
):
    """A vintage with no stock at all still contributes its own reference
    price - averages aren't limited to currently-stocked bottles."""
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    vintage.price = Decimal("25.00")
    vintage.save()

    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    expected = f"{number_format(Decimal('25.00'), use_l10n=True)}{currency}"
    with django_assert_num_queries(3):
        assert vintage.get_average_price_with_currency == expected


# ---------------------------------------------------------------------------
# Wine model property coverage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_type_label(user, wine_factory, django_assert_num_queries):
    wine = wine_factory(user=user, wine_type="RE")
    with django_assert_num_queries(0):
        assert wine.get_type == "Red"


@pytest.mark.django_db
def test_get_category_label(user, wine_factory, django_assert_num_queries):
    wine = wine_factory(user=user, wine_type="WH")
    wine.category = "DR"
    wine.save()
    with django_assert_num_queries(0):
        assert wine.get_category == "Dry"


@pytest.mark.django_db
def test_get_category_none(user, wine_factory, django_assert_num_queries):
    wine = wine_factory(user=user)
    wine.category = None
    wine.save()
    with django_assert_num_queries(0):
        assert wine.get_category is None


@pytest.mark.django_db
def test_country_name(user, wine_factory, django_assert_num_queries):
    wine = wine_factory(user=user, country="DE")
    with django_assert_num_queries(0):
        assert wine.country_name == "Germany"


@pytest.mark.django_db
def test_country_icon(user, wine_factory, django_assert_num_queries):
    wine = wine_factory(user=user, country="DE")
    with django_assert_num_queries(0):
        assert wine.country_icon  # flag emoji, non-empty


@pytest.mark.django_db
def test_total_stock_excludes_deleted(
    user, wine_factory, storage_item_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    storage = user.storage_set.first()
    storage_item_factory(vintage=vintage, storage=storage)
    storage_item_factory(vintage=vintage, storage=storage, deleted=True)
    with django_assert_num_queries(1):
        assert wine.total_stock == 1


@pytest.mark.django_db
def test_get_stock_ordering(
    user, wine_factory, storage_factory, storage_item_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    storage = storage_factory(user=user, rows=3, columns=3)
    item_b = storage_item_factory(vintage=vintage, storage=storage, row=2, column=1)
    item_a = storage_item_factory(vintage=vintage, storage=storage, row=1, column=1)
    with django_assert_num_queries(1):
        stock = list(wine.get_stock)
    assert stock[0] == item_a
    assert stock[1] == item_b


@pytest.mark.django_db
def test_get_stock_prefetches_storage(
    user, wine_factory, storage_factory, storage_item_factory
):
    """Regression guard: wine_detail.html accesses `item.storage` per row,
    so get_stock must select_related it - fetch_mode(FETCH_RAISE) fails loudly
    if that's ever dropped instead of silently reintroducing an N+1."""
    wine = wine_factory(user=user)
    storage = storage_factory(user=user, rows=1, columns=1)
    storage_item_factory(vintage=wine.latest_vintage, storage=storage, row=1, column=1)
    stock = list(wine.get_stock.fetch_mode(FETCH_RAISE))
    assert [str(item.storage) for item in stock] == [str(storage)]


@pytest.mark.django_db
def test_get_food_pairings(
    user, wine_factory, food_pairing_factory, django_assert_num_queries
):
    pairing1 = food_pairing_factory(name="Cheese")
    pairing2 = food_pairing_factory(name="Steak")
    wine = wine_factory(user=user)
    wine.food_pairings.set([pairing1, pairing2])
    with django_assert_num_queries(1):
        result = wine.get_food_pairings
    assert "Cheese" in result
    assert "Steak" in result


@pytest.mark.django_db
def test_get_attributes(
    user, wine_factory, attribute_factory, django_assert_num_queries
):
    attr1 = attribute_factory(name="Organic")
    attr2 = attribute_factory(name="Natural")
    wine = wine_factory(user=user)
    wine.attributes.set([attr1, attr2])
    with django_assert_num_queries(1):
        result = wine.get_attributes
    assert "Organic" in result
    assert "Natural" in result


@pytest.mark.django_db
def test_get_vineyards(user, wine_factory, vineyard_factory, django_assert_num_queries):
    v1 = vineyard_factory(name="Estate A")
    v2 = vineyard_factory(name="Estate B")
    wine = wine_factory(user=user)
    wine.vineyard.set([v1, v2])
    with django_assert_num_queries(1):
        result = wine.get_vineyards
    assert "Estate A" in result
    assert "Estate B" in result


@pytest.mark.django_db
def test_get_sources(user, wine_factory, source_factory, django_assert_num_queries):
    s1 = source_factory(name="Supermarket")
    s2 = source_factory(name="Winery Direct")
    wine = wine_factory(user=user)
    wine.source.set([s1, s2])
    with django_assert_num_queries(1):
        result = wine.get_sources
    assert "Supermarket" in result
    assert "Winery Direct" in result


@pytest.mark.django_db
def test_get_price_with_currency(user, vintage_factory, django_assert_num_queries):
    vintage = vintage_factory(wine__user=user, price=Decimal("14.99"))
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    with django_assert_num_queries(1):
        result = vintage.get_price_with_currency
    assert "14" in result
    assert currency in result


@pytest.mark.django_db
def test_drink_by_warning_date(user, vintage_factory, django_assert_num_queries):
    vintage = vintage_factory(wine__user=user)
    expected = datetime.date.today() + datetime.timedelta(days=30)
    with django_assert_num_queries(0):
        assert vintage.drink_by_warning_date == expected


@pytest.mark.django_db
def test_grape_str_empty_name(grape_factory, django_assert_num_queries):
    grape = grape_factory(name="")
    with django_assert_num_queries(0):
        assert str(grape) == ""


@pytest.mark.django_db
def test_wine_get_abv_range_single_value(
    user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, abv=13.0)
    with django_assert_num_queries(1):
        assert wine.get_abv_range == "13.0%"


@pytest.mark.django_db
def test_wine_get_abv_range_spans_vintages(
    user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, abv=13.0)
    vintage_factory(wine=wine, abv=14.5)
    with django_assert_num_queries(1):
        assert wine.get_abv_range == "13.0–14.5%"


@pytest.mark.django_db
def test_wine_get_abv_range_none_when_unset(
    user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, abv=None)
    with django_assert_num_queries(1):
        assert wine.get_abv_range is None


@pytest.mark.django_db
def test_wine_get_average_rating(
    user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, rating=8)
    vintage_factory(wine=wine, rating=9)
    vintage_factory(wine=wine, rating=None)  # excluded, not counted as 0
    with django_assert_num_queries(1):
        assert wine.get_average_rating == "8.5/10"


@pytest.mark.django_db
def test_wine_get_average_rating_none_when_unset(
    user, wine_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    with django_assert_num_queries(1):
        assert wine.get_average_rating is None


@pytest.mark.django_db
def test_wine_get_average_price_combines_vintages_and_reference_prices(
    user,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Unweighted average, across vintages, of each vintage's own average
    price (purchase prices plus its reference price) - a vintage with many
    bottles doesn't outweigh one with few, and one with no stock at all
    still counts via its reference price."""
    wine = wine_factory(user=user, _create_default_vintage=False)
    v1 = vintage_factory(wine=wine, price=Decimal("30.00"))
    storage_item_factory(vintage=v1, price=Decimal("10.00"))
    storage_item_factory(vintage=v1, price=Decimal("20.00"))
    # v1 average: (30 + 10 + 20) / 3 = 20.00

    vintage_factory(wine=wine, price=Decimal("50.00"))
    # v2 average: 50.00 (reference price only, no stock)

    avg = Decimal("35.00")  # (20 + 50) / 2
    currency = settings.CURRENCY_SYMBOLS.get("EUR")
    expected = f"{number_format(avg, use_l10n=True)}{currency}"
    with django_assert_num_queries(2):
        assert wine.get_average_price_with_currency == expected


@pytest.mark.django_db
def test_wine_get_average_price_none_when_unset(
    user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine)
    with django_assert_num_queries(2):
        assert wine.get_average_price_with_currency is None
