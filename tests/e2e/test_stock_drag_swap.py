"""Drag-and-drop reordering in the storage grid (StorageItemSwapView,
wine_cellar/apps/storage/views.py:588-666, JS assets/js/stock_drag.ts).
Native HTML5 drag-and-drop, AJAX POST, and a full page reload on success -
Playwright's `drag_to()` drives real dragstart/dragover/drop events against
`draggable="true"` rows."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_drag_onto_adjacent_item_swaps_positions(
    live_server, page, login, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=1, columns=2)
    item_a = storage_item_factory(
        storage=storage,
        wine=wine_factory(user=user, name="Wine A"),
        user=user,
        row=1,
        column=1,
    )
    item_b = storage_item_factory(
        storage=storage,
        wine=wine_factory(user=user, name="Wine B"),
        user=user,
        row=1,
        column=2,
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )

    source = page.locator(f"tr[data-item-id='{item_a.pk}']")
    target = page.locator(f"tr[data-item-id='{item_b.pk}']")
    with page.expect_navigation():
        source.drag_to(target)

    item_a.refresh_from_db()
    item_b.refresh_from_db()
    assert (item_a.row, item_a.column) == (1, 2)
    assert (item_b.row, item_b.column) == (1, 1)


@pytest.mark.django_db
def test_drag_onto_non_adjacent_item_shifts_the_chain(
    live_server, page, login, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=1, columns=3)
    item_a = storage_item_factory(
        storage=storage,
        wine=wine_factory(user=user, name="Wine A"),
        user=user,
        row=1,
        column=1,
    )
    item_b = storage_item_factory(
        storage=storage,
        wine=wine_factory(user=user, name="Wine B"),
        user=user,
        row=1,
        column=2,
    )
    item_c = storage_item_factory(
        storage=storage,
        wine=wine_factory(user=user, name="Wine C"),
        user=user,
        row=1,
        column=3,
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )

    # Drag A onto C: A takes C's slot, B and C each shift back one to fill
    # the gap A left behind.
    source = page.locator(f"tr[data-item-id='{item_a.pk}']")
    target = page.locator(f"tr[data-item-id='{item_c.pk}']")
    with page.expect_navigation():
        source.drag_to(target)

    item_a.refresh_from_db()
    item_b.refresh_from_db()
    item_c.refresh_from_db()
    assert (item_a.row, item_a.column) == (1, 3)
    assert (item_b.row, item_b.column) == (1, 1)
    assert (item_c.row, item_c.column) == (1, 2)


@pytest.mark.django_db
def test_drag_onto_empty_slot_moves_item_there(
    live_server, page, login, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=1, columns=2)
    item = storage_item_factory(
        storage=storage,
        wine=wine_factory(user=user, name="Lone Wine"),
        user=user,
        row=1,
        column=1,
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )

    source = page.locator(f"tr[data-item-id='{item.pk}']")
    empty_slot = page.locator("tr.card__table-empty[data-row='1'][data-column='2']")
    with page.expect_navigation():
        source.drag_to(empty_slot)

    item.refresh_from_db()
    assert (item.row, item.column) == (1, 2)
