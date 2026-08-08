"""Adding/editing stock (StorageItemAddView/UpdateView, stock_add.html) -
the cascading storage -> row -> column tom-selects driven by
assets/js/stock_add.ts, which rebuilds the row/column `<select>` options
from a JSON blob per chosen storage and shows a "row full" warning."""

import pytest
from django.urls import reverse

from tests.e2e.conftest import tom_select_pick

pytestmark = pytest.mark.e2e


def resync_slot_selects(page):
    """On the edit form, `storage` already has a value, so re-picking the
    same option through the UI doesn't fire a "change" event (the value
    never actually changes) and stock_add.ts's row/column-populating
    listener never runs, leaving them empty. Dispatching the event
    manually forces that populate step using whatever storage is currently
    selected."""
    page.eval_on_selector(
        "#id_storage", "el => el.dispatchEvent(new Event('change', {bubbles: true}))"
    )


@pytest.mark.django_db
def test_add_stock_to_a_grid_storage(
    live_server, page, login, user, wine_factory, storage_factory
):
    storage = storage_factory(user=user, name="Wine Fridge", rows=2, columns=2)
    wine = wine_factory(user=user, name="New Arrival")
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': wine.pk})}")

    tom_select_pick(page, "id_storage", "Wine Fridge")
    tom_select_pick(page, "id_row", "1")
    tom_select_pick(page, "id_column", "2")
    page.locator("#id_price").fill("15.00")
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    assert "Wine Fridge" in page.locator("main").inner_text()

    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )
    assert "New Arrival" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_full_row_shows_warning_and_disables_submit(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, name="Tiny Rack", rows=1, columns=1)
    occupant = wine_factory(user=user, name="Occupant")
    storage_item_factory(storage=storage, wine=occupant, user=user, row=1, column=1)
    wine = wine_factory(user=user, name="Newcomer")
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': wine.pk})}")

    tom_select_pick(page, "id_storage", "Tiny Rack")
    tom_select_pick(page, "id_row", "1")

    warning = page.locator("#storage__error-full")
    assert "hidden" not in (warning.get_attribute("class") or "")
    assert page.locator("#submit_button").is_disabled()


@pytest.mark.django_db
def test_unlimited_shelf_disables_slot_selects(
    live_server, page, login, user, wine_factory
):
    # Every user gets an auto-created "Default Shelf" (rows=columns=0) -
    # see wine_cellar/apps/storage/signals.py's post_save receiver on User.
    wine = wine_factory(user=user, name="Loose Bottle")
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': wine.pk})}")

    tom_select_pick(page, "id_storage", "Default Shelf")
    assert page.locator("#id_row").is_disabled()
    assert page.locator("#id_column").is_disabled()
    assert not page.locator("#submit_button").is_disabled()

    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    assert "Default Shelf" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_editing_into_a_slot_taken_after_page_load_shows_validation_error(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    """The cascading row/column selects only ever offer slots that were
    free when the page was rendered (assets/js/stock_add.ts), so getting
    to the "already occupied" server-side error through pure UI clicks
    would need the target slot to be taken *between* page load and submit -
    exactly the race this covers: someone else claims the slot right after
    this page was loaded, and the server-side check in StockForm.clean()
    is the actual safety net, not just the client-side filtering."""
    storage = storage_factory(user=user, name="Shared Rack", rows=1, columns=2)
    mover_wine = wine_factory(user=user, name="Wants To Move")
    mover_item = storage_item_factory(
        storage=storage, wine=mover_wine, user=user, row=1, column=2
    )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-edit', kwargs={'pk': mover_item.pk})}")

    # At this point column 1 is still free, and the UI happily offers it.
    resync_slot_selects(page)
    tom_select_pick(page, "id_row", "1")
    tom_select_pick(page, "id_column", "1")

    # Someone else takes column 1 before this form is submitted.
    occupant = wine_factory(user=user, name="Stays Put")
    storage_item_factory(storage=storage, wine=occupant, user=user, row=1, column=1)

    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(300)

    assert "already occupied" in page.locator("main").inner_text()
    mover_item.refresh_from_db()
    assert mover_item.column == 2


@pytest.mark.django_db
def test_editing_stock_from_storage_grid_returns_to_storage_detail(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    """Every stock action reachable from the storage grid (open, undo-open,
    consume, delete, edit) honors `?next=storage` and returns the user
    there - see wine_cellar/apps/storage/views.py's `get_success_url`
    methods, including `StorageItemUpdateView`'s."""
    storage = storage_factory(user=user, name="Grid Rack", rows=1, columns=2)
    wine = wine_factory(user=user, name="Movable")
    item = storage_item_factory(storage=storage, wine=wine, user=user, row=1, column=1)
    login(user)
    page.goto(
        f"{live_server.url}{reverse('stock-edit', kwargs={'pk': item.pk})}?next=storage"
    )

    # row/column start out empty on load - re-select the item's current
    # slot so the submission stays valid.
    resync_slot_selects(page)
    tom_select_pick(page, "id_row", "1")
    tom_select_pick(page, "id_column", "1")
    page.locator("#id_price").fill("9.99")
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('storage-detail', kwargs={'pk': storage.pk})}")
