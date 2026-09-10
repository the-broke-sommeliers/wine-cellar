import json
from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from wine_cellar.apps.wine.filters import WineMapFilter


@pytest.mark.django_db
def test_wine_map_view(client, user, wine_factory):
    wine_factory(user=user)
    client.force_login(user)
    r = client.get(reverse("wine-map"))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="wine_map.html")


@pytest.mark.django_db
def test_wine_map_view_has_no_sort_field(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-map"))
    assert r.status_code == HTTPStatus.OK
    assert "order" not in r.context_data["filter"].form.fields


@pytest.mark.django_db
def test_wine_map_filter_drops_order(rf, user):
    request = rf.get("/wines/map")
    request.user = user
    assert "order" not in WineMapFilter(data={}, request=request).filters
    assert "order" in WineMapFilter(data={}, request=request).base_filters


@pytest.mark.django_db
def test_wine_map_filter_order_param_has_no_effect(client, user, wine_factory):
    wine_factory(user=user)
    client.force_login(user)
    r = client.get(reverse("wine-map-data") + "?order=-name")
    assert r.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_wine_map_data_view_query_count_does_not_scale_with_wine_count(
    client, user, wine_factory, django_assert_num_queries
):
    wine_factory(user=user)
    client.force_login(user)
    with django_assert_num_queries(5):
        r = client.get(reverse("wine-map-data"))
    assert r.status_code == HTTPStatus.OK
    assert len(json.loads(r.content)["wines"]) == 1

    wine_factory(user=user)
    wine_factory(user=user)
    with django_assert_num_queries(5):
        r = client.get(reverse("wine-map-data"))
    assert r.status_code == HTTPStatus.OK
    assert len(json.loads(r.content)["wines"]) == 3


@pytest.mark.django_db
def test_wine_map_data_view_includes_total_stock(
    client, user, wine_factory, vintage_factory, storage_item_factory
):
    storage = user.storage_set.first()
    wine = wine_factory(user=user, name="Stocked Wine", _create_default_vintage=False)
    vintage = vintage_factory(wine=wine, year=2020)
    storage_item_factory(storage=storage, vintage=vintage)
    storage_item_factory(storage=storage, vintage=vintage)
    wine_factory(user=user, name="Empty Wine")

    client.force_login(user)
    r = client.get(reverse("wine-map-data"))
    assert r.status_code == HTTPStatus.OK
    wines_by_name = {w["name"]: w for w in json.loads(r.content)["wines"]}
    assert wines_by_name["Stocked Wine"]["total_stock"] == 2
    assert wines_by_name["Empty Wine"]["total_stock"] == 0


@pytest.mark.django_db
def test_wine_map_data_view_filter_in_stock(
    client, user, wine_factory, vintage_factory, storage_item_factory
):
    storage = user.storage_set.first()
    wine_in_stock = wine_factory(
        user=user, name="In Stock", _create_default_vintage=False
    )
    vintage_in_stock = vintage_factory(wine=wine_in_stock, year=2020)
    storage_item_factory(storage=storage, vintage=vintage_in_stock)
    wine_factory(user=user, name="Not In Stock")

    client.force_login(user)
    r = client.get(reverse("wine-map-data"))
    assert r.status_code == HTTPStatus.OK
    names = {w["name"] for w in json.loads(r.content)["wines"]}
    assert names == {"In Stock", "Not In Stock"}

    r = client.get(reverse("wine-map-data") + "?stock=1")
    assert r.status_code == HTTPStatus.OK
    names = {w["name"] for w in json.loads(r.content)["wines"]}
    assert names == {"In Stock"}


@pytest.mark.django_db
def test_wine_map_data_view_only_returns_requesting_users_wines(
    client, user, user_factory, wine_factory
):
    wine_factory(user=user, name="Mine")
    wine_factory(user=user_factory(), name="Someone Else's")

    client.force_login(user)
    r = client.get(reverse("wine-map-data"))
    assert r.status_code == HTTPStatus.OK
    names = {w["name"] for w in json.loads(r.content)["wines"]}
    assert names == {"Mine"}
