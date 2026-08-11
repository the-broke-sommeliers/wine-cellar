"""The full lifecycle of a stock item - open, undo-open, consume, delete
(wine_cellar/apps/storage/views.py) - and the History page that logs it
all (StorageItemHistoryView, storage_item_history.html)."""

import pytest
from django.urls import reverse

from wine_cellar.apps.storage.models import StorageItemEventType

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_open_bottle_with_reminder_shows_opened_styling(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=1, columns=1)
    wine = wine_factory(user=user, name="To Be Opened")
    item = storage_item_factory(storage=storage, wine=wine, user=user, row=1, column=1)
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-open', kwargs={'pk': item.pk})}")

    page.locator("#id_drink_in_days").fill("3")
    page.locator("#id_note").fill("Birthday dinner")
    page.get_by_role("button", name="Open Bottle").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    item.refresh_from_db()
    assert item.opened is True
    assert item.opened_note == "Birthday dinner"
    assert item.drink_by is not None

    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )
    assert page.locator("tr.stock-item--opened").count() == 1


@pytest.mark.django_db
def test_undo_open_reverts_state(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=1, columns=1)
    wine = wine_factory(user=user, name="Reopened")
    item = storage_item_factory(
        storage=storage,
        wine=wine,
        user=user,
        row=1,
        column=1,
        opened=True,
        opened_note="oops",
    )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-undo-open', kwargs={'pk': item.pk})}")
    page.get_by_role("button", name="Undo Opening").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    item.refresh_from_db()
    assert item.opened is False
    assert item.opened_note is None
    assert item.drink_by is None


@pytest.mark.django_db
def test_consume_sealed_bottle_directly(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    """Consuming a bottle that was never explicitly opened should still
    mark it opened+deleted (StorageItemConsumeView.form_valid)."""
    storage = storage_factory(user=user, rows=1, columns=1)
    wine = wine_factory(user=user, name="Straight To Finished")
    item = storage_item_factory(storage=storage, wine=wine, user=user, row=1, column=1)
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-consume', kwargs={'pk': item.pk})}")
    page.get_by_role("button", name="Finish Bottle").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    item.refresh_from_db()
    assert item.opened is True
    assert item.deleted is True
    assert "No bottles in stock" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_delete_item_removes_from_grid(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=1, columns=1)
    wine = wine_factory(user=user, name="Removed Bottle")
    item = storage_item_factory(storage=storage, wine=wine, user=user, row=1, column=1)
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-delete', kwargs={'pk': item.pk})}")
    page.get_by_role("button", name="Delete").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )
    assert "Removed Bottle" not in page.locator("main").inner_text()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name,button_text",
    [
        ("stock-open", "Open Bottle"),
        ("stock-consume", "Finish Bottle"),
        ("stock-delete", "Delete"),
    ],
)
def test_actions_from_storage_grid_return_to_storage_detail(
    live_server,
    page,
    login,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    url_name,
    button_text,
):
    storage = storage_factory(user=user, rows=1, columns=1)
    wine = wine_factory(user=user, name="Grid Origin")
    item = storage_item_factory(storage=storage, wine=wine, user=user, row=1, column=1)
    login(user)
    page.goto(
        f"{live_server.url}{reverse(url_name, kwargs={'pk': item.pk})}?next=storage"
    )
    page.get_by_role("button", name=button_text).click()
    page.wait_for_url(f"**{reverse('storage-detail', kwargs={'pk': storage.pk})}")


@pytest.mark.django_db
def test_history_page_shows_correct_status_per_item(
    live_server,
    page,
    login,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    storage_item_event_factory,
):
    """The history page (`StorageItemHistoryView`) lists `StorageItemEvent`
    rows, not `StorageItem`s directly - building items via the factory
    alone (as this test used to) leaves nothing for the page to show, since
    nothing but the real add/open/consume/delete views logs an event."""
    storage = storage_factory(user=user, rows=0, columns=0)
    opened_wine = wine_factory(user=user, name="History Opened")
    consumed_wine = wine_factory(user=user, name="History Consumed")
    removed_wine = wine_factory(user=user, name="History Removed")
    opened_item = storage_item_factory(
        storage=storage, wine=opened_wine, user=user, opened=True
    )
    consumed_item = storage_item_factory(
        storage=storage, wine=consumed_wine, user=user, opened=True, deleted=True
    )
    removed_item = storage_item_factory(
        storage=storage, wine=removed_wine, user=user, opened=False, deleted=True
    )
    storage_item_event_factory(
        storage_item=opened_item,
        wine=opened_wine,
        user=user,
        event_type=StorageItemEventType.OPENED,
    )
    storage_item_event_factory(
        storage_item=consumed_item,
        wine=consumed_wine,
        user=user,
        event_type=StorageItemEventType.CONSUMED,
    )
    storage_item_event_factory(
        storage_item=removed_item,
        wine=removed_wine,
        user=user,
        event_type=StorageItemEventType.REMOVED,
    )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-history')}")

    # The history page is a timeline/activity feed (storage_item_history.html),
    # not a table.
    rows_text = page.locator("ul.timeline li.timeline__item").all_inner_texts()
    combined = " | ".join(rows_text)
    assert "History Opened" in combined and "Opened" in combined
    assert "History Consumed" in combined and "Consumed" in combined
    assert "History Removed" in combined and "Removed" in combined


@pytest.mark.django_db
def test_history_pagination(
    live_server,
    page,
    login,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    storage_item_event_factory,
):
    storage = storage_factory(user=user, rows=0, columns=0)
    for i in range(11):
        wine = wine_factory(user=user, name=f"History Wine {i:02d}")
        item = storage_item_factory(storage=storage, wine=wine, user=user, opened=True)
        storage_item_event_factory(
            storage_item=item,
            wine=wine,
            user=user,
            event_type=StorageItemEventType.OPENED,
        )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-history')}")

    assert page.locator("ul.timeline li.timeline__item").count() == 10
    assert page.locator("ul.pagination li", has_text="2").count() == 1
