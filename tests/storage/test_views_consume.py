from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects

from wine_cellar.apps.storage.models import StorageItemEvent, StorageItemEventType


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
    event = StorageItemEvent.objects.get(storage_item=item)
    assert event.event_type == StorageItemEventType.CONSUMED


@pytest.mark.django_db
def test_open_then_consume_creates_two_distinct_history_events(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    """Consuming must not overwrite the earlier "opened" event."""
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    client.post(
        reverse("stock-open", kwargs={"pk": item.pk}), data={"note": "anniversary"}
    )
    client.post(reverse("stock-consume", kwargs={"pk": item.pk}))
    events = StorageItemEvent.objects.filter(storage_item=item).order_by("created")
    assert [e.event_type for e in events] == [
        StorageItemEventType.OPENED,
        StorageItemEventType.CONSUMED,
    ]
    assert events.first().note == "anniversary"


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
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    storage_item_event_factory,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, wine=wine, user=user, opened=True, deleted=True
    )
    event = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.CONSUMED
    )
    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    events = list(r.context["events"])
    pks = [e.pk for e in events]
    assert event.pk in pks
    consumed = next(e for e in events if e.pk == event.pk)
    assert consumed.event_type == StorageItemEventType.CONSUMED
