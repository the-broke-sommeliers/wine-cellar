from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertRedirects, assertTemplateUsed


@pytest.mark.django_db
def test_wine_scanned_existing(
    client,
    user,
    wine_factory,
    vintage_factory,
    django_assert_num_queries,
):
    wine = wine_factory(user=user, country="DE", _create_default_vintage=False)
    vintage = vintage_factory(wine=wine, barcode="12345")
    client.force_login(user)
    # wine_detail.html now also renders the per-vintage tab strip (a
    # "vintages" queryset + its own image prefetch, plus each tab's own
    # image/image_thumbnails lookups), on top of the wine-level image calls.
    with django_assert_num_queries(26):
        r = client.get(
            reverse("wine-scan", kwargs={"barcode": vintage.barcode}), follow=True
        )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
        + f"?vintage={vintage.pk}",
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_detail.html")


@pytest.mark.django_db
def test_wine_scanned_non_existing(
    client,
    user,
    wine_factory,
    vintage_factory,
    django_assert_num_queries,
):
    wine = wine_factory(user=user, country="DE", _create_default_vintage=False)
    vintage_factory(wine=wine, barcode="12345")
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.get(reverse("wine-scan", kwargs={"barcode": "00000"}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_scanned.html")


@pytest.mark.django_db
def test_wine_scanned_matches_multiple_different_wines(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine_a = wine_factory(user=user, country="DE", _create_default_vintage=False)
    vintage_a = vintage_factory(wine=wine_a, barcode="12345")
    wine_b = wine_factory(user=user, country="FR", _create_default_vintage=False)
    vintage_b = vintage_factory(wine=wine_b, barcode="12345")
    client.force_login(user)
    r = client.get(reverse("wine-scan", kwargs={"barcode": "12345"}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="wine_scan_multiple.html")
    assert r.context["same_wine"] is False
    content = r.content.decode()
    assert f"?vintage={vintage_a.pk}" in content
    assert f"?vintage={vintage_b.pk}" in content
    assert "Multiple wines in your cellar share the barcode" in content


@pytest.mark.django_db
def test_wine_scanned_matches_multiple_vintages_of_the_same_wine(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, country="DE", _create_default_vintage=False)
    vintage_2019 = vintage_factory(wine=wine, year=2019, barcode="12345")
    vintage_2021 = vintage_factory(wine=wine, year=2021, barcode="12345")
    client.force_login(user)
    r = client.get(reverse("wine-scan", kwargs={"barcode": "12345"}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="wine_scan_multiple.html")
    assert r.context["same_wine"] is True
    content = r.content.decode()
    assert f"?vintage={vintage_2019.pk}" in content
    assert f"?vintage={vintage_2021.pk}" in content
    assert "matches multiple vintages of the same wine" in content


@pytest.mark.django_db
def test_wine_filter_in_stock(
    client,
    user,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    storage = user.storage_set.first()
    wine_in_stock = wine_factory(user=user, _create_default_vintage=False)
    vintage_in_stock = vintage_factory(wine=wine_in_stock, year=2020)
    wine_was_in_stock = wine_factory(user=user, _create_default_vintage=False)
    vintage_was_in_stock = vintage_factory(wine=wine_was_in_stock, year=2019)
    wine_not_in_stock = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine_not_in_stock, year=2021)
    storage_item_factory(storage=storage, vintage=vintage_in_stock)
    storage_item_factory(
        storage=storage,
        vintage=vintage_was_in_stock,
        deleted=True,
    )
    client.force_login(user)
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list"))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert set(r.context_data["wines"]) == {
        wine_in_stock,
        wine_not_in_stock,
        wine_was_in_stock,
    }
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?stock=1")
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert list(r.context_data["wines"]) == [wine_in_stock]

    # Any non-"1" value (django-filter still invokes the method since the
    # value itself isn't empty) leaves the queryset unfiltered.
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?stock=0")
    assert r.status_code == HTTPStatus.OK
    assert set(r.context_data["wines"]) == {
        wine_in_stock,
        wine_not_in_stock,
        wine_was_in_stock,
    }


@pytest.mark.django_db
def test_wine_filter_price(
    client,
    user,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    storage = user.storage_set.first()
    wine_in_stock_cheap = wine_factory(user=user, _create_default_vintage=False)
    vintage_cheap = vintage_factory(wine=wine_in_stock_cheap, year=2020)
    wine_in_stock_expensive = wine_factory(user=user, _create_default_vintage=False)
    vintage_expensive = vintage_factory(wine=wine_in_stock_expensive, year=2020)
    wine_in_stock_middle = wine_factory(user=user, _create_default_vintage=False)
    vintage_middle = vintage_factory(wine=wine_in_stock_middle, year=2020)
    wine_was_in_stock = wine_factory(user=user, _create_default_vintage=False)
    vintage_was_in_stock = vintage_factory(wine=wine_was_in_stock, year=2019)
    wine_no_price = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine_no_price, year=2019)
    wine_not_in_stock = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine_not_in_stock, year=2021, price=7.00)
    storage_item_factory(storage=storage, vintage=vintage_cheap, price=5.00)
    storage_item_factory(storage=storage, vintage=vintage_middle, price=15.00)
    storage_item_factory(storage=storage, vintage=vintage_expensive, price=50.00)
    storage_item_factory(
        storage=storage,
        vintage=vintage_was_in_stock,
        price=10.00,
        deleted=True,
    )
    client.force_login(user)
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?order=-effective_price", follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert list(r.context_data["wines"]) == [
        wine_in_stock_expensive,
        wine_in_stock_middle,
        wine_was_in_stock,
        wine_not_in_stock,
        wine_in_stock_cheap,
        wine_no_price,
    ]
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?order=effective_price", follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert list(r.context_data["wines"]) == [
        wine_in_stock_cheap,
        wine_not_in_stock,
        wine_was_in_stock,
        wine_in_stock_middle,
        wine_in_stock_expensive,
        wine_no_price,
    ]


@pytest.mark.django_db
def test_wine_list_effective_price_not_skewed_by_fan_out(
    client,
    user,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Regression test: `effective_price` falls back to averaging the
    vintages' own price when no stock item has a price set. Combining that
    average with the storageitem-count annotation in one annotate() used to
    fan-out-multiply vintage rows by their (priceless) stock item count
    before averaging, over-weighting whichever vintage has more bottles."""
    storage = user.storage_set.first()
    wine = wine_factory(user=user, _create_default_vintage=False)
    # 3 (priceless) bottles of the 100-priced vintage, 1 of the 200-priced
    # one - a naive fan-out would skew the average toward 100.
    vintage_a = vintage_factory(wine=wine, year=2019, price=Decimal("100.00"))
    vintage_b = vintage_factory(wine=wine, year=2021, price=Decimal("200.00"))
    storage_item_factory(storage=storage, vintage=vintage_a, price=None)
    storage_item_factory(storage=storage, vintage=vintage_a, price=None)
    storage_item_factory(storage=storage, vintage=vintage_a, price=None)
    storage_item_factory(storage=storage, vintage=vintage_b, price=None)
    client.force_login(user)
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list"))
    assert r.status_code == HTTPStatus.OK
    result = next(w for w in r.context_data["wines"] if w.pk == wine.pk)
    assert result.effective_price == Decimal("150.00")
    assert result.total_stock_count == 4


@pytest.mark.django_db
def test_wine_filter_by_wine_type(
    client, user, wine_factory, django_assert_num_queries
):
    wine_red = wine_factory(user=user, wine_type="RE", name="Red Wine")
    wine_white = wine_factory(user=user, wine_type="WH", name="White Wine")
    client.force_login(user)
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?wine_type=RE")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_red in wines
    assert wine_white not in wines


@pytest.mark.django_db
def test_wine_filter_by_country(client, user, wine_factory, django_assert_num_queries):
    wine_de = wine_factory(user=user, country="DE", name="German Wine")
    wine_fr = wine_factory(user=user, country="FR", name="French Wine")
    client.force_login(user)
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?country=DE")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_de in wines
    assert wine_fr not in wines


@pytest.mark.django_db
def test_wine_filter_by_name(client, user, wine_factory, django_assert_num_queries):
    wine_merlot = wine_factory(user=user, name="Grand Merlot Reserve")
    wine_other = wine_factory(user=user, name="Chardonnay")
    client.force_login(user)
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?name=merlot")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_merlot in wines
    assert wine_other not in wines


@pytest.mark.django_db
def test_wine_filter_by_storage(
    client,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    storage_a = storage_factory(user=user)
    storage_b = storage_factory(user=user)
    wine_in_a = wine_factory(user=user, name="Wine in A")
    wine_in_b = wine_factory(user=user, name="Wine in B")
    wine_no_storage = wine_factory(user=user, name="Wine without storage")
    storage_item_factory(storage=storage_a, vintage=wine_in_a.latest_vintage)
    storage_item_factory(storage=storage_b, vintage=wine_in_b.latest_vintage)
    client.force_login(user)
    with django_assert_num_queries(15):
        r = client.get(reverse("wine-list") + f"?storage={storage_a.pk}")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wines == [wine_in_a]
    assert wine_in_b not in wines
    assert wine_no_storage not in wines


@pytest.mark.django_db
def test_wine_filter_by_storage_ignores_deleted_items(
    client,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    storage = storage_factory(user=user)
    wine_removed = wine_factory(user=user, name="Removed Wine")
    storage_item_factory(
        storage=storage, vintage=wine_removed.latest_vintage, deleted=True
    )
    client.force_login(user)
    with django_assert_num_queries(11):
        r = client.get(reverse("wine-list") + f"?storage={storage.pk}")
    assert r.status_code == HTTPStatus.OK
    assert wine_removed not in list(r.context_data["wines"])


@pytest.mark.django_db
def test_wine_filter_storage_options_scoped_to_user(
    client, user, user_factory, storage_factory, django_assert_num_queries
):
    own_storage = storage_factory(user=user)
    other_storage = storage_factory(user=user_factory())
    client.force_login(user)
    with django_assert_num_queries(9):
        r = client.get(reverse("wine-list"))
    assert r.status_code == HTTPStatus.OK
    storage_options = r.context_data["filter"].form.fields["storage"].queryset
    assert own_storage in storage_options
    assert other_storage not in storage_options


@pytest.mark.django_db
def test_wine_filter_by_vintage(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine_2020 = wine_factory(
        user=user, name="Vintage 2020", _create_default_vintage=False
    )
    vintage_factory(wine=wine_2020, year=2020)
    wine_2019 = wine_factory(
        user=user, name="Vintage 2019", _create_default_vintage=False
    )
    vintage_factory(wine=wine_2019, year=2019)
    client.force_login(user)
    with django_assert_num_queries(14):
        r = client.get(reverse("wine-list") + "?vintage=2020")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_2020 in wines
    assert wine_2019 not in wines


@pytest.mark.django_db
def test_wine_filter_by_vintage_combined_with_stock_has_no_duplicates(
    client,
    user,
    wine_factory,
    vintage_factory,
    storage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Stacking the vintage filter with another multi-valued-relation filter
    (stock) must not return the same wine more than once."""
    storage = storage_factory(user=user)
    wine = wine_factory(user=user, name="Multi Bottle", _create_default_vintage=False)
    vintage = vintage_factory(wine=wine, year=2020)
    storage_item_factory(storage=storage, vintage=vintage)
    storage_item_factory(storage=storage, vintage=vintage)
    client.force_login(user)
    r = client.get(reverse("wine-list") + "?vintage=2020&stock=1")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wines.count(wine) == 1


@pytest.mark.django_db
def test_wine_sort_by_drink_by(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    soon = wine_factory(user=user, name="Soon", _create_default_vintage=False)
    vintage_factory(
        wine=soon, drink_by=timezone.localdate() + timedelta(days=1), year=2020
    )
    later = wine_factory(user=user, name="Later", _create_default_vintage=False)
    vintage_factory(
        wine=later, drink_by=timezone.localdate() + timedelta(days=30), year=2020
    )
    no_date = wine_factory(user=user, name="No Date", _create_default_vintage=False)
    vintage_factory(wine=no_date, drink_by=None, year=2020)
    client.force_login(user)
    r = client.get(reverse("wine-list") + "?order=next_drink_by")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    # Soonest due date first, wines with no drink-by date sort last.
    assert wines.index(soon) < wines.index(later) < wines.index(no_date)
