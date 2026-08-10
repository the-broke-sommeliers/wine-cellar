from http import HTTPStatus

import pytest
from django.urls import reverse

from wine_cellar.apps.storage.models import StorageItemEventType
from wine_cellar.apps.wine.models import Size, Wine


@pytest.mark.django_db
def test_history_unauthenticated_redirects(client):
    r = client.get(reverse("stock-history"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assert r.redirect_chain
    assert reverse("account_login") in r.redirect_chain[0][0]


@pytest.mark.django_db
def test_history_orders_newest_first(
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
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    added = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.ADDED
    )
    opened = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.OPENED
    )
    consumed = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.CONSUMED
    )
    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    events = list(r.context["events"])
    # Events were created in ascending order, so newest-first means the
    # reverse of creation order.
    assert [e.pk for e in events] == [consumed.pk, opened.pk, added.pk]


@pytest.mark.django_db
def test_history_hides_other_users_events(
    client,
    user,
    user_factory,
    storage_factory,
    wine_factory,
    storage_item_factory,
    storage_item_event_factory,
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    own_item = storage_item_factory(storage=storage, wine=wine, user=user)
    own_event = storage_item_event_factory(storage_item=own_item, user=user)

    other_storage = storage_factory(user=other)
    other_wine = wine_factory(user=other)
    other_item = storage_item_factory(
        storage=other_storage, wine=other_wine, user=other
    )
    other_event = storage_item_event_factory(storage_item=other_item, user=other)

    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    pks = [e.pk for e in r.context["events"]]
    assert own_event.pk in pks
    assert other_event.pk not in pks


@pytest.mark.django_db
def test_history_shows_wine_added_and_removed_end_to_end(client, user):
    """Adding then deleting a wine shows up on the history page, in order,
    even after the wine itself is gone."""
    client.force_login(user)
    data = {
        "name": "Chablis 2019",
        "wine_type": "WH",
        "category": "DR",
        "size": Size.objects.get(name=0.75).pk,
        "vintage": 2019,
        "country": "FR",
    }
    client.post(reverse("wine-add"), data)
    wine = Wine.objects.get(name="Chablis 2019")
    client.post(reverse("wine-delete", kwargs={"pk": wine.pk}))

    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    assert r.content.decode().count("Chablis 2019") >= 2
    events = list(r.context["events"])
    event_types = [e.event_type for e in events]
    assert event_types.index(StorageItemEventType.WINE_REMOVED) < event_types.index(
        StorageItemEventType.WINE_ADDED
    )


@pytest.mark.django_db
def test_history_renders_as_activity_feed(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    storage_item_event_factory,
):
    """Sanity check that the timeline template actually renders - one
    .timeline__item per event, with its icon class present."""
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    event = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.OPENED
    )

    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    content = r.content.decode()
    assert content.count("timeline__item") == 1
    assert event.icon_class in content
    assert f"timeline__icon--{event.css_modifier}" in content


@pytest.mark.django_db
def test_history_pagination(
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
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    for _ in range(11):
        storage_item_event_factory(storage_item=item, user=user)

    r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    assert len(r.context["events"]) == 10

    r = client.get(reverse("stock-history") + "?page=2")
    assert r.status_code == HTTPStatus.OK
    assert len(r.context["events"]) == 1
