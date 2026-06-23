from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects

from wine_cellar.apps.storage.models import StorageItem  # noqa: F401


@pytest.mark.django_db
def test_unauthenticated_cant_undo_open(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user, opened=True)
    r = client.get(reverse("stock-undo-open", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("stock-undo-open", kwargs={"pk": item.pk}),
    )


@pytest.mark.django_db
def test_undo_open_clears_opened_and_reminder(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    from datetime import date, timedelta

    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage,
        wine=wine,
        user=user,
        opened=True,
        opened_note="birthday dinner",
        drink_by=date.today() + timedelta(days=7),
    )
    r = client.post(reverse("stock-undo-open", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("wine-detail", kwargs={"pk": wine.pk}))
    item.refresh_from_db()
    assert item.opened is False
    assert item.opened_note is None
    assert item.drink_by is None


@pytest.mark.django_db
def test_undo_open_redirects_to_storage_detail(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user, opened=True)
    r = client.post(
        reverse("stock-undo-open", kwargs={"pk": item.pk}) + "?next=storage",
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("storage-detail", kwargs={"pk": storage.pk}))


@pytest.mark.django_db
def test_cant_undo_open_on_unopened_bottle(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    r = client.get(reverse("stock-undo-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_cant_undo_open_on_deleted_bottle(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, wine=wine, user=user, opened=True, deleted=True
    )
    r = client.get(reverse("stock-undo-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_cant_undo_open_other_users_bottle(
    client, user, user_factory, storage_factory, wine_factory, storage_item_factory
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=other)
    wine = wine_factory(user=other)
    item = storage_item_factory(storage=storage, wine=wine, user=other, opened=True)
    r = client.get(reverse("stock-undo-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND
