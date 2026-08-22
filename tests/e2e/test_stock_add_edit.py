"""Adding/editing stock via the clickable slot-picker grid
(assets/js/stock_add.ts)."""

from decimal import Decimal

import pytest
from django.urls import reverse

from tests.e2e.conftest import tom_select_pick

pytestmark = pytest.mark.e2e


def grid_cell(page, row, column):
    return page.locator(f'#grid-picker__table button[data-key="{row},{column}"]')


@pytest.mark.django_db
def test_add_stock_to_a_grid_storage(
    live_server, page, login, user, wine_factory, storage_factory
):
    storage = storage_factory(user=user, name="Wine Fridge", rows=2, columns=2)
    wine = wine_factory(user=user, name="New Arrival")
    login(user)
    vintage_pk = wine.latest_vintage.pk
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': vintage_pk})}")

    tom_select_pick(page, "id_storage", "Wine Fridge")
    grid_cell(page, 1, 2).click()
    page.locator("#id_price").fill("15.00")
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    assert "Wine Fridge" in page.locator("main").inner_text()

    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )
    assert "New Arrival" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_add_multiple_bottles_by_clicking_cells(
    live_server, page, login, user, wine_factory, storage_factory
):
    storage = storage_factory(user=user, name="Wine Fridge", rows=2, columns=2)
    wine = wine_factory(user=user, name="Case Delivery")
    login(user)
    vintage_pk = wine.latest_vintage.pk
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': vintage_pk})}")

    tom_select_pick(page, "id_storage", "Wine Fridge")
    grid_cell(page, 1, 1).click()
    grid_cell(page, 1, 2).click()
    grid_cell(page, 2, 1).click()
    assert "3" in page.locator("#grid-picker__count").inner_text()

    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    assert storage.used_slots == 3
    coords = set(storage.items.values_list("row", "column"))
    assert coords == {(1, 1), (1, 2), (2, 1)}


@pytest.mark.django_db
def test_auto_fill_selects_first_free_cells(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, name="Wine Fridge", rows=2, columns=2)
    occupant = wine_factory(user=user, name="Occupant")
    storage_item_factory(
        storage=storage, vintage=occupant.latest_vintage, user=user, row=1, column=1
    )
    wine = wine_factory(user=user, name="Auto Filled")
    login(user)
    vintage_pk = wine.latest_vintage.pk
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': vintage_pk})}")

    tom_select_pick(page, "id_storage", "Wine Fridge")
    page.locator("#id_quantity").fill("2")
    page.locator("#grid-picker__autofill").click()

    assert "2" in page.locator("#grid-picker__count").inner_text()
    assert "selected" in (grid_cell(page, 1, 2).get_attribute("class") or "")
    assert "selected" in (grid_cell(page, 2, 1).get_attribute("class") or "")

    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    assert storage.used_slots == 3


@pytest.mark.django_db
def test_full_grid_disables_all_cells_and_submit(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, name="Tiny Rack", rows=1, columns=1)
    occupant = wine_factory(user=user, name="Occupant")
    storage_item_factory(
        storage=storage, vintage=occupant.latest_vintage, user=user, row=1, column=1
    )
    wine = wine_factory(user=user, name="Newcomer")
    login(user)
    vintage_pk = wine.latest_vintage.pk
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': vintage_pk})}")

    tom_select_pick(page, "id_storage", "Tiny Rack")
    assert grid_cell(page, 1, 1).is_disabled()
    assert page.locator("#submit_button").is_disabled()


@pytest.mark.django_db
def test_wide_grid_scrolls_horizontally_on_narrow_viewport(
    live_server, page, login, user, wine_factory, storage_factory
):
    """A shelf too wide for a narrow viewport must scroll inside the picker,
    not widen the whole page."""
    storage_factory(user=user, name="Wide Rack", rows=1, columns=12)
    wine = wine_factory(user=user, name="Somewhere In There")
    login(user)
    page.set_viewport_size({"width": 376, "height": 800})
    vintage_pk = wine.latest_vintage.pk
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': vintage_pk})}")

    tom_select_pick(page, "id_storage", "Wide Rack")

    page_width = page.evaluate("document.documentElement.scrollWidth")
    assert page_width <= 376 + 1  # +1 for sub-pixel rounding

    scroll = page.locator(".grid-picker__scroll")
    scroll_width = scroll.evaluate("el => el.scrollWidth")
    client_width = scroll.evaluate("el => el.clientWidth")
    assert scroll_width > client_width

    # Bounding box, not is_visible(), since that ignores scroll clipping.
    def right_edge():
        return grid_cell(page, 1, 12).evaluate("el => el.getBoundingClientRect().right")

    assert right_edge() > 376
    scroll.evaluate("el => el.scrollLeft = el.scrollWidth")
    assert right_edge() <= 376 + 1


@pytest.mark.django_db
def test_unlimited_shelf_hides_grid_picker(
    live_server, page, login, user, wine_factory
):
    # Auto-created "Default Shelf" - see storage/signals.py.
    wine = wine_factory(user=user, name="Loose Bottle")
    login(user)
    vintage_pk = wine.latest_vintage.pk
    page.goto(f"{live_server.url}{reverse('stock-add', kwargs={'pk': vintage_pk})}")

    tom_select_pick(page, "id_storage", "Default Shelf")
    assert "hidden" in (page.locator("#grid-picker").get_attribute("class") or "")
    assert not page.locator("#submit_button").is_disabled()

    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    assert "Default Shelf" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_editing_preselects_current_slot(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    """The edit form preselects the bottle's current slot."""
    storage = storage_factory(user=user, name="Grid Rack", rows=1, columns=2)
    wine = wine_factory(user=user, name="Movable")
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, row=1, column=1
    )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-edit', kwargs={'pk': item.pk})}")

    assert "selected" in (grid_cell(page, 1, 1).get_attribute("class") or "")
    assert not page.locator("#submit_button").is_disabled()

    page.locator("#id_price").fill("9.99")
    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    item.refresh_from_db()
    assert item.row == 1
    assert item.column == 1
    assert item.price == Decimal("9.99")


@pytest.mark.django_db
def test_editing_into_a_slot_taken_after_page_load_shows_validation_error(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    """StockForm.clean() is the real safety net, not just the client-side
    picker - a slot taken after page load must still be rejected."""
    storage = storage_factory(user=user, name="Shared Rack", rows=1, columns=2)
    mover_wine = wine_factory(user=user, name="Wants To Move")
    mover_item = storage_item_factory(
        storage=storage, vintage=mover_wine.latest_vintage, user=user, row=1, column=2
    )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-edit', kwargs={'pk': mover_item.pk})}")

    # At this point column 1 is still free, and the UI happily offers it.
    grid_cell(page, 1, 1).click()

    # Someone else takes column 1 before this form is submitted.
    occupant = wine_factory(user=user, name="Stays Put")
    storage_item_factory(
        storage=storage, vintage=occupant.latest_vintage, user=user, row=1, column=1
    )

    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(300)

    assert "already occupied" in page.locator("main").inner_text()
    mover_item.refresh_from_db()
    assert mover_item.column == 2


@pytest.mark.django_db
def test_editing_stock_from_storage_grid_returns_to_storage_detail(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    """`?next=storage` returns the user to the storage grid after editing."""
    storage = storage_factory(user=user, name="Grid Rack", rows=1, columns=2)
    wine = wine_factory(user=user, name="Movable")
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, row=1, column=1
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('stock-edit', kwargs={'pk': item.pk})}?next=storage"
    )

    # The current slot is already preselected - just change the price.
    page.locator("#id_price").fill("9.99")
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('storage-detail', kwargs={'pk': storage.pk})}")


@pytest.mark.django_db
def test_editing_switch_to_different_storage_requires_new_slot(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    """Switching storage drops the preselected slot - a fresh pick is
    required to submit."""
    storage = storage_factory(user=user, name="Grid Rack", rows=1, columns=1)
    other_storage = storage_factory(user=user, name="Other Rack", rows=1, columns=1)
    wine = wine_factory(user=user, name="Movable")
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, row=1, column=1
    )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-edit', kwargs={'pk': item.pk})}")

    tom_select_pick(page, "id_storage", "Other Rack")
    assert page.locator("#submit_button").is_disabled()

    grid_cell(page, 1, 1).click()
    assert not page.locator("#submit_button").is_disabled()

    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    item.refresh_from_db()
    assert item.storage == other_storage
    assert item.row == 1
    assert item.column == 1


@pytest.mark.django_db
def test_editing_switch_to_unlimited_storage_needs_no_slot(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, name="Grid Rack", rows=1, columns=1)
    wine = wine_factory(user=user, name="Movable")
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, row=1, column=1
    )
    login(user)
    page.goto(f"{live_server.url}{reverse('stock-edit', kwargs={'pk': item.pk})}")

    tom_select_pick(page, "id_storage", "Default Shelf")
    assert "hidden" in (page.locator("#grid-picker").get_attribute("class") or "")
    assert not page.locator("#submit_button").is_disabled()

    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    item.refresh_from_db()
    assert item.row is None
    assert item.column is None
