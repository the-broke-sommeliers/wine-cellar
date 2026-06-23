from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects

from wine_cellar.apps.storage.models import StorageItem  # noqa: F401


@pytest.mark.django_db
def test_unauthenticated_cant_consume_stock(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    r = client.get(reverse("stock-consume", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("stock-consume", kwargs={"pk": item.pk}),
    )


@pytest.mark.django_db
def test_consume_unopened_bottle(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    r = client.post(reverse("stock-consume", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("wine-detail", kwargs={"pk": wine.pk}))
    item.refresh_from_db()
    assert item.opened is True
    assert item.deleted is True


@pytest.mark.django_db
def test_consume_already_opened_bottle(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user, opened=True)
    r = client.post(reverse("stock-consume", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    item.refresh_from_db()
    assert item.opened is True
    assert item.deleted is True


@pytest.mark.django_db
def test_consume_redirects_to_storage_detail(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    r = client.post(
        reverse("stock-consume", kwargs={"pk": item.pk}) + "?next=storage",
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("storage-detail", kwargs={"pk": storage.pk}))


@pytest.mark.django_db
def test_cant_consume_already_deleted_bottle(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user, deleted=True)
    r = client.get(reverse("stock-consume", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_cant_consume_other_users_bottle(
    client, user, user_factory, storage_factory, wine_factory, storage_item_factory
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=other)
    wine = wine_factory(user=other)
    item = storage_item_factory(storage=storage, wine=wine, user=other)
    r = client.get(reverse("stock-consume", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_history_shows_consumed(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, wine=wine, user=user, opened=True, deleted=True
    )
    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    items = list(r.context["storage_items"])
    pks = [i.pk for i in items]
    assert item.pk in pks
    consumed = next(i for i in items if i.pk == item.pk)
    assert consumed.opened is True
    assert consumed.deleted is True
