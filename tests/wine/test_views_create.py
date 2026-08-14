import datetime
import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed

from tests.helpers import random_png
from wine_cellar.apps.storage.models import StorageItemEvent, StorageItemEventType
from wine_cellar.apps.wine.models import ImageType, Size, Wine, WineImage


def _wine_add_redirect(client, poll_url):
    """Given the `poll_url` from POSTing to `wine-ai-upload`, poll it until
    done and return the final `wine-add?prefill_token=...` URL.
    `CELERY_TASK_ALWAYS_EAGER=True` (test.py) means the task has already
    finished by the time the initial POST returns, so a single poll always
    reflects the final state."""
    r = client.get(poll_url)
    data = r.json()
    assert data["status"] == "done", data
    return data["redirect"]


@pytest.mark.django_db
def test_wine_create_unauthenticated(client, user, django_assert_num_queries):
    with django_assert_num_queries(1):
        r = client.get(reverse("wine-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login") + "?next=" + reverse("wine-add"),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_wine_create(client, user, django_assert_num_queries):
    client.force_login(user)
    with django_assert_num_queries(11):
        r = client.get(reverse("wine-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")


@pytest.mark.django_db
def test_wine_create_with_grapes(
    client, user, grape_factory, django_assert_num_queries
):
    grape1 = grape_factory()
    grape2 = grape_factory()
    client.force_login(user)
    with django_assert_num_queries(11):
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
def test_wine_create_post_empty(client, user, django_assert_num_queries):
    client.force_login(user)
    data = {}
    with django_assert_num_queries(11):
        r = client.post(reverse("wine-add"), data)
    assert r.status_code == HTTPStatus.OK
    f = r.context["form"]
    assert not f.is_valid()
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_create_post_unauthenticated(client, django_assert_num_queries):
    with django_assert_num_queries(1):
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
def test_wine_create_post_with_barcode(client, user, django_assert_num_queries):
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
    r = client.get(reverse("wine-add-choose") + "?barcode=12345")
    token = r.context_data["prefill_token"]
    r = client.get(reverse("wine-add") + f"?prefill_token={token}")
    initial = r.context_data["form"].initial.copy()
    initial.update(data)
    with django_assert_num_queries(32):
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
def test_wine_create_post_with_drink_by(client, user, django_assert_num_queries):
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
    r = client.get(reverse("wine-add-choose") + "?barcode=12345")
    token = r.context_data["prefill_token"]
    r = client.get(reverse("wine-add") + f"?prefill_token={token}")
    initial = r.context_data["form"].initial.copy()
    initial.update(data)
    with django_assert_num_queries(32):
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
def test_wine_create_post_with_invalid_drink_by(
    client, user, django_assert_num_queries
):
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
    r = client.get(reverse("wine-add-choose") + "?barcode=12345")
    token = r.context_data["prefill_token"]
    r = client.get(reverse("wine-add") + f"?prefill_token={token}")
    initial = r.context_data["form"].initial.copy()
    initial.update(data)
    with django_assert_num_queries(12):
        r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors


@pytest.mark.django_db
def test_wine_create_post_with_steps(
    client, user, region_factory, appellation_factory, django_assert_num_queries
):
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
    with django_assert_num_queries(12):
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
    with django_assert_num_queries(12):
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
    with django_assert_num_queries(14):
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
    with django_assert_num_queries(14):
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
    with django_assert_num_queries(14):
        r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert not Wine.objects.exists()

    # post form step 5
    initial = r.context_data["form"].data.copy()
    assert initial["form_step"] == 5
    with django_assert_num_queries(41):
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
def test_wine_create_post_invalid_step(client, user, django_assert_num_queries):
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
    with django_assert_num_queries(12):
        r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    assert r.context_data["form"].errors
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_create_post_valid(client, user, django_assert_num_queries):
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
    with django_assert_num_queries(32):
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
    event = StorageItemEvent.objects.get(wine=wine)
    assert event.event_type == StorageItemEventType.WINE_ADDED
    assert event.wine_name == wine.name


@pytest.mark.django_db
def test_wine_create_save_finish_commits_early(client, user, django_assert_num_queries):
    """The "Save & Finish" button lets the user commit from any wizard
    step - `"save_finish" in self.request.POST` short-circuits the normal
    `form_step == 5` requirement. Every other wizard test drives `form_step`
    up to 5 naturally; this pins the shortcut itself."""
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
        "form_step": 0,
        "save_finish": "1",
    }
    assert not Wine.objects.exists()
    with django_assert_num_queries(32):
        r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assert Wine.objects.exists()
    wine = Wine.objects.first()
    assert wine.name == "Merlot"


@pytest.mark.django_db
def test_wine_update_does_not_log_wine_added(
    client, user, wine, django_assert_num_queries
):
    """Editing an existing wine reuses the same create-flow form_valid logic
    as WineCreateView - it must not log a second WINE_ADDED event."""
    client.force_login(user)
    data = {
        "name": wine.name,
        "wine_type": wine.wine_type,
        "category": "DR",
        "size": Size.objects.get(name=0.75).pk,
        "country": wine.country,
    }
    with django_assert_num_queries(43):
        client.post(reverse("wine-edit", kwargs={"pk": wine.pk}), data, follow=True)
    assert not StorageItemEvent.objects.filter(
        event_type=StorageItemEventType.WINE_ADDED
    ).exists()


@pytest.mark.django_db
def test_wine_create_post_single_grape_valid(
    client, user, grape_factory, django_assert_num_queries
):
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
    with django_assert_num_queries(37):
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
def test_wine_create_post_multiple_grape_valid(
    client, user, grape_factory, django_assert_num_queries
):
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
    with django_assert_num_queries(37):
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
def test_wine_create_post_new_grape_valid(
    client, user, grape_factory, django_assert_num_queries
):
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
    with django_assert_num_queries(40):
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
def test_wine_create_post_invalid_grape(
    client, user, grape_factory, django_assert_num_queries
):
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
    with django_assert_num_queries(11):
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
    with django_assert_num_queries(13):
        r = client.post(reverse("wine-add"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    f = r.context["form"]
    assert not f.is_valid()
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_create.html")
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_create_post_new_grape_multiple_valid(
    client, user, grape_factory, django_assert_num_queries
):
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
    with django_assert_num_queries(41):
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
    django_assert_num_queries,
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
    with django_assert_num_queries(53):
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
def test_wine_create_duplicate(client, user, wine_factory, django_assert_num_queries):
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
    with django_assert_num_queries(16):
        r = client.post(reverse("wine-add"), data=initial)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors
    assert Wine.objects.count() == 1


@pytest.mark.django_db
def test_wine_create_continue_advances_step(client, user, django_assert_num_queries):
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
    with django_assert_num_queries(12):
        r = client.post(reverse("wine-add"), data=data)
    assert r.status_code == HTTPStatus.OK
    form = r.context["form"]
    assert int(form["form_step"].value()) == 1
    content = r.content.decode()
    assert 'id="create__fs_1"' in content
    assert 'id="create__fs_1" class="hidden"' not in content


@pytest.mark.django_db
def test_wine_create_back_goes_to_previous_step(
    client, user, django_assert_num_queries
):
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
    with django_assert_num_queries(12):
        r = client.post(reverse("wine-add"), data={**data, "back": ""})
    assert r.status_code == HTTPStatus.OK
    assert int(r.context["form"]["form_step"].value()) == 0
    assert 'id="create__fs_0"' in r.content.decode()


@pytest.mark.django_db
def test_wine_create_back_does_not_go_below_zero(
    client, user, django_assert_num_queries
):
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
    with django_assert_num_queries(12):
        r = client.post(reverse("wine-add"), data={**data, "back": ""})
    assert r.status_code == HTTPStatus.OK
    assert int(r.context["form"]["form_step"].value()) == 0


@pytest.mark.django_db
def test_wine_edit_replace_front_image(
    client, user, wine_factory, clear_image_folder, django_assert_num_queries
):
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

    with django_assert_num_queries(51):
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

    with django_assert_num_queries(54):
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
def test_wine_edit_overwrite_front_and_back_with_newer_images(
    client, user, wine_factory, clear_image_folder, django_assert_num_queries
):
    """Uploading new front/back images for a wine that already has images should
    replace them in place (no duplicate rows) and store the newer files."""
    wine = wine_factory(user=user)
    client.force_login(user)
    size = Size.objects.first()

    base_data = {
        "name": wine.name,
        "wine_type": wine.wine_type,
        "country": wine.country,
        "size": size.pk,
    }

    with django_assert_num_queries(57):
        r = client.post(
            reverse("wine-edit", kwargs={"pk": wine.pk}),
            {
                **base_data,
                "image_front": random_png("front_old.png"),
                "image_back": random_png("back_old.png"),
            },
            follow=True,
        )
    assert r.status_code == HTTPStatus.OK
    assert WineImage.objects.filter(wine=wine, image_type=ImageType.FRONT).count() == 1
    assert WineImage.objects.filter(wine=wine, image_type=ImageType.BACK).count() == 1

    with django_assert_num_queries(64):
        r = client.post(
            reverse("wine-edit", kwargs={"pk": wine.pk}),
            {
                **base_data,
                "image_front": random_png("front_new.png"),
                "image_back": random_png("back_new.png"),
            },
            follow=True,
        )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )

    front_images = WineImage.objects.filter(wine=wine, image_type=ImageType.FRONT)
    back_images = WineImage.objects.filter(wine=wine, image_type=ImageType.BACK)
    # Overwriting must not leave the old row (and file) behind.
    assert front_images.count() == 1
    assert back_images.count() == 1
    assert "front_new" in front_images.first().image.name
    assert "front_old" not in front_images.first().image.name
    assert "back_new" in back_images.first().image.name
    assert "back_old" not in back_images.first().image.name


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_wine_create_overwriting_ai_stashed_images_with_newer_ones(
    mock_completion, client, user, clear_image_folder, django_assert_num_queries
):
    """Manually uploading newer front/back images on the create form should
    overwrite the images stashed from the AI upload step, for both fields at
    once, without creating duplicate rows."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "AI Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)

    with django_assert_num_queries(2):
        r = client.post(
            reverse("wine-ai-upload"),
            data={
                "front": random_png("ai_front.png"),
                "back": random_png("ai_back.png"),
                "use_as_wine_images": "on",
            },
        )
    assert r.status_code == HTTPStatus.OK

    r = client.get(_wine_add_redirect(client, r.json()["poll_url"]))
    initial = {k: v for k, v in r.context_data["form"].initial.items() if v is not None}

    size = Size.objects.get(name=0.75)
    initial.update(
        {
            "name": "AI Wine",
            "wine_type": "RE",
            "category": "DR",
            "abv": 13.0,
            "size": size.pk,
            "vintage": 2002,
            "country": "DE",
            "form_step": 5,
            "image_front": random_png("newer_front.png"),
            "image_back": random_png("newer_back.png"),
        }
    )
    with django_assert_num_queries(45):
        r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))

    wine = Wine.objects.first()
    front_images = WineImage.objects.filter(wine=wine, image_type=ImageType.FRONT)
    back_images = WineImage.objects.filter(wine=wine, image_type=ImageType.BACK)
    assert front_images.count() == 1
    assert back_images.count() == 1
    assert "newer_front" in front_images.first().image.name
    assert "ai_front" not in front_images.first().image.name
    assert "newer_back" in back_images.first().image.name
    assert "ai_back" not in back_images.first().image.name


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_wine_create_uses_ai_uploaded_front_image(
    mock_completion, client, user, clear_image_folder, django_assert_num_queries
):
    """Front image uploaded to the AI form should become the wine's front image
    without having to be re-uploaded on the create form."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "AI Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)

    with django_assert_num_queries(2):
        r = client.post(
            reverse("wine-ai-upload"),
            data={"front": random_png("ai_front.png"), "use_as_wine_images": "on"},
        )
    assert r.status_code == HTTPStatus.OK
    wine_add_url = _wine_add_redirect(client, r.json()["poll_url"])
    assert "prefill_token" in wine_add_url

    with django_assert_num_queries(11):
        r = client.get(wine_add_url)
    assert r.status_code == HTTPStatus.OK
    initial = {k: v for k, v in r.context_data["form"].initial.items() if v is not None}
    assert initial["prefill_token"]

    size = Size.objects.get(name=0.75)
    initial.update(
        {
            "name": "AI Wine",
            "wine_type": "RE",
            "category": "DR",
            "abv": 13.0,
            "size": size.pk,
            "vintage": 2002,
            "country": "DE",
            "form_step": 5,
        }
    )
    with django_assert_num_queries(39):
        r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    wine = Wine.objects.first()
    assert WineImage.objects.filter(wine=wine, image_type=ImageType.FRONT).count() == 1


@pytest.mark.django_db
def test_wine_create_prefill_not_visible_to_other_user(
    client, user, user_factory, django_assert_num_queries
):
    """A guessed/observed `prefill_token` from someone else's AI-scan or
    barcode "Add Manually" flow must not prefill or stash images for a
    different logged-in user."""
    client.force_login(user)
    r = client.get(reverse("wine-add-choose") + "?barcode=9780201633610")
    token = r.context_data["prefill_token"]

    other_user = user_factory()
    client.force_login(other_user)
    with django_assert_num_queries(11):
        r = client.get(reverse("wine-add") + f"?prefill_token={token}")
    assert r.status_code == HTTPStatus.OK
    initial = {k: v for k, v in r.context_data["form"].initial.items() if v is not None}
    assert "barcode" not in initial
    assert r.context_data["ai_images_pending"] is False

    # the original owner's entry must be untouched
    data = caches["wine_prefill"].get(f"wine_prefill_{token}")
    assert data["user_id"] == user.pk
    assert data["initial"]["barcode"] == "9780201633610"


@pytest.mark.django_db
def test_wine_create_other_users_prefill_token_not_deleted_on_save(
    client, user, user_factory, django_assert_num_queries
):
    """Saving a wine while presenting someone else's `prefill_token` must not
    delete that other user's still-valid cache entry."""
    client.force_login(user)
    r = client.get(reverse("wine-add-choose") + "?barcode=9780201633610")
    token = r.context_data["prefill_token"]

    other_user = user_factory()
    client.force_login(other_user)
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
        "prefill_token": token,
    }
    with django_assert_num_queries(32):
        r = client.post(reverse("wine-add"), data=data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))

    assert caches["wine_prefill"].get(f"wine_prefill_{token}") is not None


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_wine_create_explicit_image_overrides_ai_stashed_image(
    mock_completion, client, user, clear_image_folder, django_assert_num_queries
):
    """Manually selecting a front image on the create form should take
    precedence over an image stashed from the AI upload step."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "AI Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)

    r = client.post(
        reverse("wine-ai-upload"),
        data={"front": random_png("ai_front.png"), "use_as_wine_images": "on"},
    )
    r = client.get(_wine_add_redirect(client, r.json()["poll_url"]))
    initial = {k: v for k, v in r.context_data["form"].initial.items() if v is not None}

    size = Size.objects.get(name=0.75)
    initial.update(
        {
            "name": "AI Wine",
            "wine_type": "RE",
            "category": "DR",
            "abv": 13.0,
            "size": size.pk,
            "vintage": 2002,
            "country": "DE",
            "form_step": 5,
            "image_front": random_png("manual_front.png"),
        }
    )
    with django_assert_num_queries(39):
        r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    wine = Wine.objects.first()
    images = WineImage.objects.filter(wine=wine, image_type=ImageType.FRONT)
    assert images.count() == 1
    assert "manual_front" in images.first().image.name
    assert "ai_front" not in images.first().image.name


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_wine_create_shows_preview_of_ai_stashed_image(
    mock_completion, client, user, clear_image_folder, django_assert_num_queries
):
    """The create form should show a live preview (with its usual clear button)
    of an image stashed from the AI upload step, before it has been saved."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "AI Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)

    with django_assert_num_queries(2):
        r = client.post(
            reverse("wine-ai-upload"),
            data={"front": random_png("ai_front.png"), "use_as_wine_images": "on"},
        )
    assert r.status_code == HTTPStatus.OK

    with django_assert_num_queries(13):
        r = client.get(_wine_add_redirect(client, r.json()["poll_url"]))
    assert r.status_code == HTTPStatus.OK
    form = r.context_data["form"]

    front_field = form["image_front"]
    assert front_field.value().url.startswith("data:image/png;base64,")

    # Render just this field's widget so assertions aren't polluted by the
    # other (empty, still-hidden) image fields on the same page.
    front_html = str(front_field)
    assert "data:image/png;base64," in front_html
    # The wrapper must not carry the "hidden" class, and the usual clear
    # button/checkbox for the field must be rendered alongside the preview.
    assert "image-preview-wrapper hidden" not in front_html
    assert "image-clear-btn" in front_html
    assert 'name="image_front-clear"' in front_html


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_wine_create_clearing_ai_stashed_image_discards_it(
    mock_completion, client, user, clear_image_folder, django_assert_num_queries
):
    """Checking the clear checkbox for the stashed AI image should behave like
    clearing any other image field: the wine ends up with no front image."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "AI Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)

    r = client.post(
        reverse("wine-ai-upload"),
        data={"front": random_png("ai_front.png"), "use_as_wine_images": "on"},
    )
    r = client.get(_wine_add_redirect(client, r.json()["poll_url"]))
    initial = {k: v for k, v in r.context_data["form"].initial.items() if v is not None}
    initial.pop("image_front", None)

    size = Size.objects.get(name=0.75)
    initial.update(
        {
            "name": "AI Wine",
            "wine_type": "RE",
            "category": "DR",
            "abv": 13.0,
            "size": size.pk,
            "vintage": 2002,
            "country": "DE",
            "form_step": 5,
            "image_front-clear": "on",
        }
    )
    with django_assert_num_queries(33):
        r = client.post(reverse("wine-add"), data=initial, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    wine = Wine.objects.first()
    assert WineImage.objects.filter(wine=wine, image_type=ImageType.FRONT).count() == 0


@pytest.mark.django_db
def test_wine_create_new_open_field_value_preserved_across_steps(
    client, user, django_assert_num_queries
):
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
    with django_assert_num_queries(12):
        r = client.post(reverse("wine-add"), data=initial)
    assert r.status_code == HTTPStatus.OK
    form = r.context_data["form"]
    assert form.data["form_step"] == 1
    tom_config = json.loads(form.fields["grapes"].widget.attrs["data-tom_config"])
    assert "Chardonnay" in tom_config.get("items", [])
