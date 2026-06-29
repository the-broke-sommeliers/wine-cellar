from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed

from wine_cellar.apps.wine.models import Size, Wine


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
