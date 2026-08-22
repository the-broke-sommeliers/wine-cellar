from http import HTTPStatus

import pytest
from django.urls import reverse

from wine_cellar.apps.storage.models import StorageItemEventType
from wine_cellar.apps.wine.models import Size, Wine


@pytest.mark.django_db
def test_history_unauthenticated_redirects(client, django_assert_num_queries):
    with django_assert_num_queries(1):
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
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    added = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.ADDED
    )
    opened = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.OPENED
    )
    consumed = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.CONSUMED
    )
    with django_assert_num_queries(4):
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
    django_assert_num_queries,
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    own_item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user
    )
    own_event = storage_item_event_factory(storage_item=own_item, user=user)

    other_storage = storage_factory(user=other)
    other_wine = wine_factory(user=other)
    other_item = storage_item_factory(
        storage=other_storage, vintage=other_wine.latest_vintage, user=other
    )
    other_event = storage_item_event_factory(storage_item=other_item, user=other)

    with django_assert_num_queries(4):
        r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    pks = [e.pk for e in r.context["events"]]
    assert own_event.pk in pks
    assert other_event.pk not in pks


@pytest.mark.django_db
def test_history_shows_wine_added_and_removed_end_to_end(
    client, user, django_assert_num_queries
):
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
    with django_assert_num_queries(9):
        client.post(reverse("wine-add"), data)
    wine = Wine.objects.get(name="Chablis 2019")
    with django_assert_num_queries(20):
        client.post(reverse("wine-delete", kwargs={"pk": wine.pk}))

    with django_assert_num_queries(4):
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
    django_assert_num_queries,
):
    """Sanity check that the timeline template actually renders - one
    .timeline__item per event, with its icon class present."""
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    event = storage_item_event_factory(
        storage_item=item, user=user, event_type=StorageItemEventType.OPENED
    )

    with django_assert_num_queries(4):
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
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    for _ in range(11):
        storage_item_event_factory(storage_item=item, user=user)

    with django_assert_num_queries(4):
        r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    assert len(r.context["events"]) == 10

    with django_assert_num_queries(4):
        r = client.get(reverse("stock-history") + "?page=2")
    assert r.status_code == HTTPStatus.OK
    assert len(r.context["events"]) == 1
