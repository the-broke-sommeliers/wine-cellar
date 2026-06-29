import datetime
import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import httpx
import litellm.exceptions
import pytest
from django.test import override_settings
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateNotUsed,
    assertTemplateUsed,
)

from tests.helpers import random_png
from wine_cellar.apps.wine.models import ImageType, Size, Wine, WineImage


def _make_litellm_exc(exc_cls, status=503):
    req = httpx.Request("POST", "https://api.example.com/")
    resp = httpx.Response(status, request=req)
    return exc_cls("test error", llm_provider="test", model="test", response=resp)


@pytest.mark.django_db
def test_homepage_unauthenticated(client):
    r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("account_login") + "?next=/")
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_homepage(client, user):
    client.force_login(user)
    r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="homepage.html")
    assertTemplateNotUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_homepage_stats(client, user, wine_factory, storage_item_factory):
    wine = wine_factory(user=user, vintage=2020)
    storage = user.storage_set.first()
    wine_2 = wine_factory(user=user, country="DE", vintage=2023, price=15.00)
    wine_factory(user=user, country="ES", vintage=2024)
    storage_item_factory(wine=wine, storage=storage, price=10.50)
    storage_item_factory(wine=wine, storage=storage, price=5.25)
    storage_item_factory(wine=wine, storage=storage, price=8.99, deleted=True)
    storage_item_factory(wine=wine_2, storage=storage, price=4.99, deleted=True)
    storage_item_factory(wine=wine_2, storage=storage, price=12.00)
    storage_item_factory(wine=wine_2, storage=storage)
    client.force_login(user)
    r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="homepage.html")
    assertTemplateNotUsed(response=r, template_name="registration/login.html")
    assert r.context_data["oldest"] == 2020
    assert r.context_data["youngest"] == 2024
    # we only count wines in stock, not bottles
    assert r.context_data["wines_in_stock"] == 2
    assert r.context_data["wines"] == 3
    assert r.context_data["countries"] == 2
    assert r.context_data["total_value"] == "43€"


@pytest.mark.django_db
def test_wine_create_unauthenticated(client, user):
    r = client.get(reverse("wine-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login") + "?next=" + reverse("wine-add"),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_wine_create(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")


@pytest.mark.django_db
def test_wine_create_with_grapes(client, user, grape_factory):
    grape1 = grape_factory()
    grape2 = grape_factory()
    client.force_login(user)
    r = client.get(reverse("wine-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    f = r.context["form"]
    grapes = [pk for pk, name in f.fields["grapes"].choices]
    assert len(grapes) == 2
    assert grape1.pk in grapes
    assert grape2.pk in grapes


@pytest.mark.django_db
def test_wine_create_post_empty(client, user):
    client.force_login(user)
    data = {}
    r = client.post(reverse("wine-add"), data)
    assert r.status_code == HTTPStatus.OK
    f = r.context["form"]
    assert not f.is_valid()
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_create_post_unauthenticated(client):
    r = client.post(reverse("wine-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login") + "?next=" + reverse("wine-add"),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_create_post_with_barcode(client, user):
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data = {
        "name": "Merlot",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "country": "DE",
        "form_step": 5,
    }
    assert not Wine.objects.exists()
    r = client.get(reverse("wine-add") + "?barcode=12345")
    initial = r.context_data["form"].initial.copy()
    initial.update(data)
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]
    assert wine.barcode == "12345"


@pytest.mark.django_db
def test_wine_create_post_with_drink_by(client, user):
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data = {
        "name": "Merlot",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "drink_by": "2003-02-25",
        "country": "DE",
        "form_step": 5,
    }
    assert not Wine.objects.exists()
    r = client.get(reverse("wine-add") + "?barcode=12345")
    initial = r.context_data["form"].initial.copy()
    initial.update(data)
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]
    assert wine.barcode == "12345"
    assert wine.drink_by == datetime.date(day=25, month=2, year=2003)


@pytest.mark.django_db
def test_wine_create_post_with_invalid_drink_by(client, user):
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data = {
        "name": "Merlot",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "drink_by": "02-02-2000",
        "country": "DE",
        "form_step": 5,
    }
    assert not Wine.objects.exists()
    r = client.get(reverse("wine-add") + "?barcode=12345")
    initial = r.context_data["form"].initial.copy()
    initial.update(data)
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors


@pytest.mark.django_db
def test_wine_create_post_with_steps(client, user, region_factory, appellation_factory):
    region = region_factory(name="Rheinhessen")
    appellation = appellation_factory(name="Nierstein")
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data_step0 = {
        "name": "Merlot",
        "wine_type": "RE",
        "size": size.pk,
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.get(reverse("wine-add"))
    initial = r.context_data["form"].initial.copy()
    assert initial["form_step"] == 0
    initial.update(data_step0)
    # post form step 1
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert not Wine.objects.exists()

    # post form step 1
    data_step1 = {
        "category": "DR",
        "abv": 13.0,
        "vintage": 2002,
    }
    initial = r.context_data["form"].data.copy()
    assert initial["form_step"] == 1
    initial.update(data_step1)
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert not Wine.objects.exists()

    # post form step 2
    data_step2 = {
        "region": region.pk,
        "appellation": appellation.pk,
    }
    initial = r.context_data["form"].data.copy()
    assert initial["form_step"] == 2
    initial.update(data_step2)
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert not Wine.objects.exists()

    # post form step 3
    data_step3 = {
        "source": "tom_new_optSupermarket",
    }
    initial = r.context_data["form"].data.copy()
    assert initial["form_step"] == 3
    initial.update(data_step3)
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert not Wine.objects.exists()

    # post form step 4
    data_step4 = {
        "rating": 5,
        "comment": "Good wine",
    }
    initial = r.context_data["form"].data.copy()
    assert initial["form_step"] == 4
    initial.update(data_step4)
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert not Wine.objects.exists()

    # post form step 5
    initial = r.context_data["form"].data.copy()
    assert initial["form_step"] == 5
    r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    data = {}
    data.update(data_step0)
    data.update(data_step1)
    data.update(data_step2)
    data.update(data_step3)
    data.update(data_step4)
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.country == data["country"]
    assert wine.region == region
    assert wine.appellation == appellation
    assert wine.vintage == data["vintage"]
    assert wine.comment == data["comment"]
    assert wine.rating == data["rating"]


@pytest.mark.django_db
def test_wine_create_post_invalid_step(client, user):
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data = {
        "name": "Merlot",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "country": "DE",
        "form_step": 6,
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    assert r.context_data["form"].errors
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_create_post_valid(client, user):
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data = {
        "name": "Merlot",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]


@pytest.mark.django_db
def test_wine_create_post_single_grape_valid(client, user, grape_factory):
    grape1 = grape_factory()
    grape_factory()
    size = Size.objects.get(name=0.75)
    client.force_login(user)
    data = {
        "name": "Wine Single Grape",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "grapes": grape1.pk,
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]
    assert wine.grapes.count() == 1
    assert wine.grapes.first() == grape1


@pytest.mark.django_db
def test_wine_create_post_multiple_grape_valid(client, user, grape_factory):
    grape1 = grape_factory()
    grape2 = grape_factory()
    size = Size.objects.get(name=0.75)
    client.force_login(user)
    data = {
        "name": "Wine Single Grape",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "grapes": [grape1.pk, grape2.pk],
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]
    assert wine.grapes.count() == 2
    assert wine.grapes.filter(id__in=[grape1.pk, grape2.pk])


@pytest.mark.django_db
def test_wine_create_post_new_grape_valid(client, user, grape_factory):
    size = Size.objects.get(name=0.75)
    client.force_login(user)
    data = {
        "name": "Wine Single Grape",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "grapes": "tom_new_optTestGrape",
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]
    assert wine.grapes.count() == 1
    assert wine.grapes.first().name == "TestGrape"


@pytest.mark.django_db
def test_wine_create_post_invalid_grape(client, user, grape_factory):
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data = {
        "name": "Wine Single Grape",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "capacity": size.pk,
        "vintage": 2002,
        "grapes": [1.0],
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    f = r.context["form"]
    assert not f.is_valid()
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    assert not Wine.objects.exists()
    data = {
        "name": "Wine Single Grape",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "grapes": 1,
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    f = r.context["form"]
    assert not f.is_valid()
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_create_post_new_grape_multiple_valid(client, user, grape_factory):
    grape1 = grape_factory()
    grape2 = grape_factory()
    size = Size.objects.get(name=0.75)
    client.force_login(user)
    data = {
        "name": "Wine Single Grape",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "grapes": ["tom_new_optTestGrape", grape1.pk, grape2.pk],
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]
    assert wine.grapes.count() == 3
    assert wine.grapes.filter(id__in=[grape1.pk, grape2.pk])
    assert wine.grapes.filter(name="TestGrape")


@pytest.mark.django_db
def test_wine_create_post_all_valid_fields(
    client,
    user,
    grape_factory,
    food_pairing_factory,
    source_factory,
    attribute_factory,
    vineyard_factory,
):
    grape1 = grape_factory()
    grape_factory()
    food_pairing = food_pairing_factory()
    source = source_factory()
    vineyard = vineyard_factory()
    attribute = attribute_factory()
    size = Size.objects.get(name=0.75)
    client.force_login(user)
    data = {
        "name": "Wine All",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "grapes": grape1.pk,
        "food_pairings": food_pairing.pk,
        "source": source.pk,
        "vineyard": vineyard.pk,
        "attributes": attribute.pk,
        "country": "DE",
    }
    assert not Wine.objects.exists()
    r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_list.html")
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert wine.abv == data["abv"]
    assert wine.size == size
    assert wine.vintage == data["vintage"]
    assert wine.grapes.count() == 1
    assert wine.grapes.first() == grape1
    assert wine.food_pairings.count() == 1
    assert wine.food_pairings.first() == food_pairing
    assert wine.vineyard.count() == 1
    assert wine.vineyard.first() == vineyard
    assert wine.source.count() == 1
    assert wine.source.first() == source
    assert wine.attributes.count() == 1


@pytest.mark.django_db
def test_wine_create_duplicate(client, user, wine_factory):
    size = Size.objects.get(name=0.75)
    wine_factory(
        user=user,
        name="Merlot",
        wine_type="RE",
        abv=13.0,
        size=size,
        vintage=2002,
        country="DE",
    )
    client.force_login(user)
    data = {
        "name": "Merlot",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "country": "DE",
        "form_step": 5,
    }
    r = client.get(reverse("wine-add"))
    initial = r.context_data["form"].initial.copy()
    initial.update(data)
    r = client.post(reverse("wine-add"), data=initial)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors
    assert Wine.objects.count() == 1


@pytest.mark.django_db
def test_wine_update_duplicate(client, user, wine_factory):
    size = Size.objects.get(name=0.75)
    wine1 = wine_factory(
        user=user,
        name="Merlot",
        wine_type="RE",
        abv=13.0,
        size=size,
        vintage=2002,
        country="DE",
    )
    wine2 = wine_factory(
        user=user,
        name="Chardonnay",
        wine_type="WH",
        abv=12.0,
        size=size,
        vintage=2020,
        country="FR",
    )
    client.force_login(user)
    data = {
        "name": wine1.name,
        "wine_type": wine1.wine_type,
        "category": "DR",
        "abv": wine1.abv,
        "size": size.pk,
        "vintage": wine1.vintage,
        "country": wine1.country,
    }
    r = client.post(reverse("wine-edit", kwargs={"pk": wine2.pk}), data)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors
    wine2.refresh_from_db()
    assert wine2.name == "Chardonnay"


@pytest.mark.django_db
def test_wine_update_valid_fields(
    client,
    user,
    wine,
    grape_factory,
    food_pairing_factory,
    source_factory,
    attribute_factory,
    vineyard_factory,
):
    grape1 = grape_factory()
    grape_factory()
    food_pairing = food_pairing_factory()
    source = source_factory()
    vineyard = vineyard_factory()
    attribute = attribute_factory()
    size = Size.objects.get(name=0.75)
    client.force_login(user)
    data = {
        "name": wine.name,
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "vintage": 2002,
        "grapes": grape1.pk,
        "food_pairings": food_pairing.pk,
        "source": source.pk,
        "vineyard": vineyard.pk,
        "attributes": attribute.pk,
        "country": "DE",
    }
    r = client.post(reverse("wine-edit", kwargs={"pk": wine.pk}), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_detail.html")
    changed_wine = Wine.objects.first()
    assert changed_wine.name == wine.name
    assert changed_wine.wine_type == data["wine_type"]
    assert changed_wine.abv == data["abv"]
    assert changed_wine.size == size
    assert changed_wine.vintage == data["vintage"]
    assert changed_wine.grapes.count() == 1
    assert changed_wine.grapes.first() == grape1
    assert changed_wine.food_pairings.count() == 1
    assert changed_wine.food_pairings.first() == food_pairing
    assert changed_wine.vineyard.count() == 1
    assert changed_wine.vineyard.first() == vineyard
    assert changed_wine.source.count() == 1
    assert changed_wine.source.first() == source
    assert changed_wine.attributes.count() == 1


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
def test_wine_create_continue_advances_step(client, user):
    """Clicking Continue on step 0 should advance to step 1 and show step 1 fields."""
    client.force_login(user)
    size = Size.objects.first()
    data = {
        "name": "Test Wine",
        "wine_type": "RE",
        "country": "DE",
        "size": size.pk,
        "form_step": 0,
    }
    r = client.post(reverse("wine-add"), data=data)
    assert r.status_code == HTTPStatus.OK
    form = r.context["form"]
    assert int(form["form_step"].value()) == 1
    content = r.content.decode()
    assert 'id="create__fs_1"' in content
    assert 'id="create__fs_1" class="hidden"' not in content


@pytest.mark.django_db
def test_wine_create_back_goes_to_previous_step(client, user):
    """Clicking Back on step 1 should return to step 0 and show step 0 fields."""
    client.force_login(user)
    size = Size.objects.first()
    data = {
        "name": "Test Wine",
        "wine_type": "RE",
        "country": "DE",
        "size": size.pk,
        "form_step": 1,
    }
    r = client.post(reverse("wine-add"), data={**data, "back": ""})
    assert r.status_code == HTTPStatus.OK
    assert int(r.context["form"]["form_step"].value()) == 0
    assert 'id="create__fs_0"' in r.content.decode()


@pytest.mark.django_db
def test_wine_create_back_does_not_go_below_zero(client, user):
    """Back on step 0 should stay at step 0."""
    client.force_login(user)
    size = Size.objects.first()
    data = {
        "name": "Test Wine",
        "wine_type": "RE",
        "country": "DE",
        "size": size.pk,
        "form_step": 0,
    }
    r = client.post(reverse("wine-add"), data={**data, "back": ""})
    assert r.status_code == HTTPStatus.OK
    assert int(r.context["form"]["form_step"].value()) == 0


@pytest.mark.django_db
def test_wine_edit_replace_front_image(client, user, wine_factory, clear_image_folder):
    """Replacing an existing front image on edit should succeed without error."""
    wine = wine_factory(user=user)
    client.force_login(user)
    size = Size.objects.first()

    base_data = {
        "name": wine.name,
        "wine_type": wine.wine_type,
        "country": wine.country,
        "size": size.pk,
    }

    r = client.post(
        reverse("wine-edit", kwargs={"pk": wine.pk}),
        {**base_data, "image_front": random_png("front1.png")},
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert WineImage.objects.filter(wine=wine, image_type=ImageType.FRONT).count() == 1

    r = client.post(
        reverse("wine-edit", kwargs={"pk": wine.pk}),
        {**base_data, "image_front": random_png("front2.png")},
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )


@pytest.mark.django_db
def test_wine_create_new_open_field_value_preserved_across_steps(client, user):
    """New values entered in OpenMultipleChoiceField must appear in TomSelect items
    on the re-rendered form so the browser keeps them selected on subsequent steps."""
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    r = client.get(reverse("wine-add"))
    initial = r.context_data["form"].initial.copy()
    initial.update(
        {
            "name": "Merlot",
            "wine_type": "RE",
            "size": size.pk,
            "country": "DE",
            "grapes": ["tom_new_optChardonnay"],
            "form_step": 0,
        }
    )
    r = client.post(reverse("wine-add"), data=initial)
    assert r.status_code == HTTPStatus.OK
    form = r.context_data["form"]
    assert form.data["form_step"] == 1
    tom_config = json.loads(form.fields["grapes"].widget.attrs["data-tom_config"])
    assert "Chardonnay" in tom_config.get("items", [])


# ---------------------------------------------------------------------------
# WineDetailView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wine_detail_authenticated(client, user, wine_factory):
    wine = wine_factory(user=user)
    client.force_login(user)
    r = client.get(reverse("wine-detail", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="wine_detail.html")


@pytest.mark.django_db
def test_wine_detail_unauthenticated(client, user, wine_factory):
    wine = wine_factory(user=user)
    r = client.get(reverse("wine-detail", kwargs={"pk": wine.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("wine-detail", kwargs={"pk": wine.pk}),
    )


@pytest.mark.django_db
def test_wine_detail_other_user_returns_404(client, user, user_factory, wine_factory):
    other_user = user_factory()
    wine = wine_factory(user=other_user)
    client.force_login(user)
    r = client.get(reverse("wine-detail", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# WineDeleteView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wine_delete(client, user, wine_factory):
    wine = wine_factory(user=user)
    client.force_login(user)
    r = client.post(reverse("wine-delete", kwargs={"pk": wine.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_delete_other_user_returns_404(client, user, user_factory, wine_factory):
    other_user = user_factory()
    wine = wine_factory(user=other_user)
    client.force_login(user)
    r = client.post(reverse("wine-delete", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert Wine.objects.count() == 1


# ---------------------------------------------------------------------------
# WineChooseActionView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wine_choose_action_ai_disabled(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-add-choose"))
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["ai_enabled"] is False


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
def test_wine_choose_action_ai_enabled(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-add-choose"))
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["ai_enabled"] is True


# ---------------------------------------------------------------------------
# WineMapView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wine_map_view(client, user, wine_factory):
    wine_factory(user=user)
    client.force_login(user)
    r = client.get(reverse("wine-map"))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="wine_map.html")


# ---------------------------------------------------------------------------
# WineUploadAIView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ai_upload_no_images_rejected(client, user):
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_success_redirects_to_create(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert reverse("wine-add") in r["Location"]
    assert "ai_initial" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_json_inside_markdown_block(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '```json\n{"name": "Test Wine"}\n```'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert "ai_initial" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_invalid_json_shows_error(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "not valid json at all"
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_authentication_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.AuthenticationError, status=401
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_rate_limit_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.RateLimitError, status=429
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_service_unavailable_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.ServiceUnavailableError, status=503
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_timeout_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.Timeout(
        "timeout", model="test", llm_provider="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_connection_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.APIConnectionError(
        "connection error", llm_provider="test", model="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


# ---------------------------------------------------------------------------
# WineFilter — additional filter fields
# ---------------------------------------------------------------------------


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


@pytest.mark.django_db
def test_wine_choose_action_with_barcode(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-add-choose") + "?barcode=9780201633610")
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["barcode"] == "9780201633610"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_back_image_only(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"back": random_png("back.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert "ai_initial" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_success_with_barcode_param(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    url = reverse("wine-ai-upload") + "?barcode=12345"
    r = client.post(url, data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert "barcode=12345" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_api_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.APIError(
        status_code=500, message="api error", llm_provider="test", model="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
def test_health_check(client):
    r = client.get(reverse("health_check"))
    assert r.status_code == HTTPStatus.OK
    import json as _json

    data = _json.loads(r.content)
    assert data["status"] == "ok"
