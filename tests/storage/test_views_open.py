from datetime import timedelta
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertRedirects

from wine_cellar.apps.storage.models import StorageItemEvent, StorageItemEventType


@pytest.mark.django_db
def test_unauthenticated_cant_open_stock(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    with django_assert_num_queries(1):
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
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    data = {"note": "birthday dinner"}
    with django_assert_num_queries(34):
        r = client.post(
            reverse("stock-open", kwargs={"pk": item.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("wine-detail", kwargs={"pk": wine.pk}))
    item.refresh_from_db()
    assert item.opened is True
    assert item.deleted is False
    assert item.opened_note == "birthday dinner"
    event = StorageItemEvent.objects.get(storage_item=item)
    assert event.event_type == StorageItemEventType.OPENED
    assert event.note == "birthday dinner"


@pytest.mark.django_db
def test_user_can_open_with_drink_reminder(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    item = storage_item_factory(storage=storage, vintage=vintage, user=user)
    original_drink_by = vintage.drink_by
    data = {"drink_in_days": 7}
    with django_assert_num_queries(34):
        r = client.post(
            reverse("stock-open", kwargs={"pk": item.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    item.refresh_from_db()
    assert item.opened is True
    assert item.drink_by == timezone.localdate() + timedelta(days=7)
    vintage.refresh_from_db()
    assert vintage.drink_by == original_drink_by


@pytest.mark.django_db
def test_user_can_open_stock_from_storage_detail(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    with django_assert_num_queries(21):
        r = client.post(
            reverse("stock-open", kwargs={"pk": item.pk}) + "?next=storage",
            data={},
            follow=True,
        )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(r, reverse("storage-detail", kwargs={"pk": storage.pk}))


@pytest.mark.django_db
def test_user_cant_open_other_users_stock(
    client,
    user,
    user_factory,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=other)
    wine = wine_factory(user=other)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=other
    )
    with django_assert_num_queries(3):
        r = client.get(reverse("stock-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_user_cant_open_already_deleted_stock(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, deleted=True
    )
    with django_assert_num_queries(3):
        r = client.get(reverse("stock-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_user_cant_open_already_opened_stock(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, opened=True
    )
    with django_assert_num_queries(3):
        r = client.get(reverse("stock-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_open_confirmation_shows_the_specific_vintage_being_opened(
    client,
    user,
    storage_factory,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user)
    wine = wine_factory(user=user, _create_default_vintage=False)
    older_vintage = vintage_factory(wine=wine, user=user, year=2015, rating=6)
    vintage_factory(wine=wine, user=user, year=2021, rating=9)
    assert wine.latest_vintage.year == 2021
    item = storage_item_factory(storage=storage, vintage=older_vintage, user=user)
    with django_assert_num_queries(11):
        r = client.get(reverse("stock-open", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.OK
    content = r.content.decode()
    assert "2015" in content
    assert "2021" not in content


@pytest.mark.django_db
def test_history_shows_opened_and_deleted_items(
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
    deleted_item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, deleted=True
    )
    removed_event = storage_item_event_factory(
        storage_item=deleted_item, user=user, event_type=StorageItemEventType.REMOVED
    )
    opened_item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, opened=True
    )
    opened_event = storage_item_event_factory(
        storage_item=opened_item, user=user, event_type=StorageItemEventType.OPENED
    )
    # An item with no events at all (e.g. never touched) has nothing to show.
    storage_item_factory(storage=storage, vintage=wine.latest_vintage, user=user)
    with django_assert_num_queries(5):
        r = client.get(reverse("stock-history"))
    assert r.status_code == HTTPStatus.OK
    events = list(r.context["events"])
    pks = [e.pk for e in events]
    assert removed_event.pk in pks
    assert opened_event.pk in pks
