from datetime import date, timedelta
from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects

from wine_cellar.apps.storage.models import StorageItem  # noqa: F401


@pytest.mark.django_db
def test_unauthenticated_cant_open_stock(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    r = client.get(reverse("stock-open", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("stock-open", kwargs={"pk": item.pk}),
    )


@pytest.mark.django_db
def test_user_can_open_stock_from_wine_detail(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    data = {"note": "birthday dinner"}
    r = client.post(
        reverse("stock-open", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("wine-detail", kwargs={"pk": wine.pk}))
    item.refresh_from_db()
    assert item.opened is True
    assert item.deleted is False
    assert item.opened_note == "birthday dinner"


@pytest.mark.django_db
def test_user_can_open_and_consume_stock(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    data = {"mark_consumed": True}
    r = client.post(
        reverse("stock-open", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    item.refresh_from_db()
    assert item.opened is True
    assert item.deleted is True


@pytest.mark.django_db
def test_user_can_open_with_drink_reminder(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    item = storage_item_factory(storage=storage, vintage=vintage, user=user)
    original_drink_by = vintage.drink_by
    data = {"drink_in_days": 7}
    r = client.post(
        reverse("stock-open", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    item.refresh_from_db()
    assert item.opened is True
    assert item.drink_by == date.today() + timedelta(days=7)
    vintage.refresh_from_db()
    assert vintage.drink_by == original_drink_by


@pytest.mark.django_db
def test_user_can_open_stock_from_storage_detail(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    r = client.post(
        reverse("stock-open", kwargs={"pk": item.pk}) + "?next=storage",
        data={},
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("storage-detail", kwargs={"pk": storage.pk}))


@pytest.mark.django_db
def test_user_cant_open_other_users_stock(
    client, user, user_factory, storage_factory, wine_factory, storage_item_factory
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=other)
    wine = wine_factory(user=other)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=other
    )
    r = client.get(reverse("stock-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_user_cant_open_already_deleted_stock(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, deleted=True
    )
    r = client.get(reverse("stock-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_user_cant_open_already_opened_stock(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, opened=True
    )
    r = client.get(reverse("stock-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_history_shows_opened_and_deleted_items(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    deleted_item = storage_item_factory(
        storage=storage, vintage=vintage, user=user, deleted=True
    )
    opened_item = storage_item_factory(
        storage=storage, vintage=vintage, user=user, opened=True
    )
    active_item = storage_item_factory(storage=storage, vintage=vintage, user=user)
    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    items = list(r.context["storage_items"])
    pks = [i.pk for i in items]
    assert deleted_item.pk in pks
    assert opened_item.pk in pks
    assert active_item.pk not in pks
