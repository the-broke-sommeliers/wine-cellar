import datetime
from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateNotUsed,
    assertTemplateUsed,
)

from tests.helpers import random_png
from wine_cellar.apps.wine.models import ImageType, Size, Wine, WineImage


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
def test_homepage_stats(client, user, vintage_factory, storage_item_factory):
    vintage = vintage_factory(wine__user=user, year=2020)
    storage = user.storage_set.first()
    vintage_2 = vintage_factory(
        wine__user=user, wine__country="DE", year=2023, price=15.00
    )
    vintage_factory(wine__user=user, wine__country="ES", year=2024)
    storage_item_factory(vintage=vintage, storage=storage, price=10.50)
    storage_item_factory(vintage=vintage, storage=storage, price=5.25)
    storage_item_factory(vintage=vintage, storage=storage, price=8.99, deleted=True)
    storage_item_factory(vintage=vintage_2, storage=storage, price=4.99, deleted=True)
    storage_item_factory(vintage=vintage_2, storage=storage, price=12.00)
    storage_item_factory(vintage=vintage_2, storage=storage)
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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]
    assert vintage.barcode == "12345"


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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]
    assert vintage.barcode == "12345"
    assert vintage.drink_by == datetime.date(day=25, month=2, year=2003)


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
        "year": 2002,
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
    vintage = wine.latest_vintage
    data = {}
    data.update(data_step0)
    data.update(data_step1)
    data.update(data_step2)
    data.update(data_step3)
    data.update(data_step4)
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert wine.country == data["country"]
    assert wine.region == region
    assert wine.appellation == appellation
    assert vintage.year == data["year"]
    assert vintage.comment == data["comment"]
    assert vintage.rating == data["rating"]


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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]


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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]
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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]
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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]
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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]
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
        "year": 2002,
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
    vintage = wine.latest_vintage
    assert wine.name == data["name"]
    assert wine.wine_type == data["wine_type"]
    assert vintage.abv == data["abv"]
    assert wine.size == size
    assert vintage.year == data["year"]
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
        "year": 2002,
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
    changed_vintage = changed_wine.latest_vintage
    assert changed_wine.name == wine.name
    assert changed_wine.wine_type == data["wine_type"]
    assert changed_vintage.abv == data["abv"]
    assert changed_wine.size == size
    assert changed_vintage.year == data["year"]
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
    vintage_factory,
):
    vintage = vintage_factory(wine__user=user, wine__country="DE", barcode="12345")
    wine = vintage.wine
    client.force_login(user)
    r = client.get(reverse("wine-scan", kwargs={"barcode": "12345"}), follow=True)
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
    vintage_factory,
):
    vintage_factory(wine__user=user, barcode="12345")
    client.force_login(user)
    r = client.get(reverse("wine-scan", kwargs={"barcode": "00000"}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_scanned.html")


@pytest.mark.django_db
def test_wine_filter_in_stock(client, user, wine_factory, storage_item_factory):
    storage = user.storage_set.first()
    wine_in_stock = wine_factory(user=user)
    wine_was_in_stock = wine_factory(user=user)
    wine_not_in_stock = wine_factory(user=user)
    storage_item_factory(storage=storage, vintage=wine_in_stock.latest_vintage)
    storage_item_factory(
        storage=storage,
        vintage=wine_was_in_stock.latest_vintage,
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
def test_wine_filter_price(
    client, user, wine_factory, vintage_factory, storage_item_factory
):
    storage = user.storage_set.first()
    wine_in_stock_cheap = wine_factory(user=user)
    wine_in_stock_expensive = wine_factory(user=user)
    wine_in_stock_middle = wine_factory(user=user)
    wine_was_in_stock = wine_factory(user=user)
    wine_no_price = wine_factory(user=user)
    vintage_not_in_stock = vintage_factory(wine__user=user, price=7.00)
    wine_not_in_stock = vintage_not_in_stock.wine
    storage_item_factory(
        storage=storage, vintage=wine_in_stock_cheap.latest_vintage, price=5.00
    )
    storage_item_factory(
        storage=storage, vintage=wine_in_stock_middle.latest_vintage, price=15.00
    )
    storage_item_factory(
        storage=storage, vintage=wine_in_stock_expensive.latest_vintage, price=50.00
    )
    storage_item_factory(
        storage=storage,
        vintage=wine_was_in_stock.latest_vintage,
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
    assert (
        WineImage.objects.filter(vintage__wine=wine, image_type=ImageType.FRONT).count()
        == 1
    )

    r = client.post(
        reverse("wine-edit", kwargs={"pk": wine.pk}),
        {**base_data, "image_front": random_png("front2.png")},
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert (
        WineImage.objects.filter(vintage__wine=wine, image_type=ImageType.FRONT).count()
        == 1
    )
