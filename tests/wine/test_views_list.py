from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed


@pytest.mark.django_db
def test_wine_scanned_existing(
    client,
    user,
    wine_factory,
):
    wine = wine_factory(user=user, country="DE", barcode="12345")
    client.force_login(user)
    r = client.get(reverse("wine-scan", kwargs={"barcode": wine.barcode}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_detail.html")


@pytest.mark.django_db
def test_wine_scanned_non_existing(
    client,
    user,
    wine_factory,
):
    wine_factory(user=user, country="DE", barcode="12345")
    client.force_login(user)
    r = client.get(reverse("wine-scan", kwargs={"barcode": "00000"}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_scanned.html")


@pytest.mark.django_db
def test_wine_filter_in_stock(client, user, wine_factory, storage_item_factory):
    storage = user.storage_set.first()
    wine_in_stock = wine_factory(user=user, vintage=2020)
    wine_was_in_stock = wine_factory(user=user, vintage=2019)
    wine_not_in_stock = wine_factory(user=user, vintage=2021)
    storage_item_factory(storage=storage, wine=wine_in_stock)
    storage_item_factory(
        storage=storage,
        wine=wine_was_in_stock,
        deleted=True,
    )
    client.force_login(user)
    r = client.get(reverse("wine-list"))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert set(r.context_data["wines"]) == {
        wine_in_stock,
        wine_not_in_stock,
        wine_was_in_stock,
    }
    r = client.get(reverse("wine-list") + "?stock=1")
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert list(r.context_data["wines"]) == [wine_in_stock]


@pytest.mark.django_db
def test_wine_filter_price(client, user, wine_factory, storage_item_factory):
    storage = user.storage_set.first()
    wine_in_stock_cheap = wine_factory(user=user, vintage=2020)
    wine_in_stock_expensive = wine_factory(user=user, vintage=2020)
    wine_in_stock_middle = wine_factory(user=user, vintage=2020)
    wine_was_in_stock = wine_factory(user=user, vintage=2019)
    wine_no_price = wine_factory(user=user, vintage=2019)
    wine_not_in_stock = wine_factory(user=user, vintage=2021, price=7.00)
    storage_item_factory(storage=storage, wine=wine_in_stock_cheap, price=5.00)
    storage_item_factory(storage=storage, wine=wine_in_stock_middle, price=15.00)
    storage_item_factory(storage=storage, wine=wine_in_stock_expensive, price=50.00)
    storage_item_factory(
        storage=storage,
        wine=wine_was_in_stock,
        price=10.00,
        deleted=True,
    )
    client.force_login(user)
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
def test_wine_filter_by_wine_type(client, user, wine_factory):
    wine_red = wine_factory(user=user, wine_type="RE", name="Red Wine")
    wine_white = wine_factory(user=user, wine_type="WH", name="White Wine")
    client.force_login(user)
    r = client.get(reverse("wine-list") + "?wine_type=RE")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_red in wines
    assert wine_white not in wines


@pytest.mark.django_db
def test_wine_filter_by_country(client, user, wine_factory):
    wine_de = wine_factory(user=user, country="DE", name="German Wine")
    wine_fr = wine_factory(user=user, country="FR", name="French Wine")
    client.force_login(user)
    r = client.get(reverse("wine-list") + "?country=DE")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_de in wines
    assert wine_fr not in wines


@pytest.mark.django_db
def test_wine_filter_by_name(client, user, wine_factory):
    wine_merlot = wine_factory(user=user, name="Grand Merlot Reserve")
    wine_other = wine_factory(user=user, name="Chardonnay")
    client.force_login(user)
    r = client.get(reverse("wine-list") + "?name=merlot")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_merlot in wines
    assert wine_other not in wines


@pytest.mark.django_db
def test_wine_filter_by_vintage(client, user, wine_factory):
    wine_2020 = wine_factory(user=user, vintage=2020, name="Vintage 2020")
    wine_2019 = wine_factory(user=user, vintage=2019, name="Vintage 2019")
    client.force_login(user)
    r = client.get(reverse("wine-list") + "?vintage=2020")
    assert r.status_code == HTTPStatus.OK
    wines = list(r.context_data["wines"])
    assert wine_2020 in wines
    assert wine_2019 not in wines
