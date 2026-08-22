"""Storage CRUD (StorageCreateView/UpdateView/DeleteView) and the resulting
detail grid's row/column ordering + label-naming-link visibility - the
swap_axes/row_labels_enabled/column_labels_enabled features new on this
branch (wine_cellar/apps/storage/views.py, storage_detail.html).

None of StorageForm's fields are actual `<select>` elements (rows/columns
are number inputs, the three toggles are checkboxes), so no TomSelect
interaction is needed here despite the page loading that bundle."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_create_storage_with_grid_and_toggles(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('storage-add')}")

    page.locator("#id_name").fill("Cellar Rack")
    page.locator("#id_location").fill("Basement")
    page.locator("#id_rows").fill("3")
    page.locator("#id_columns").fill("4")
    page.locator("#id_swap_axes").check()
    page.locator("#id_row_labels_enabled").uncheck()
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('storage-list')}")
    assert "Cellar Rack" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_edit_storage_persists_changes(live_server, page, login, user, storage_factory):
    storage = storage_factory(user=user, name="Old Name", rows=2, columns=2)
    login(user)
    page.goto(f"{live_server.url}{reverse('storage-edit', kwargs={'pk': storage.pk})}")

    page.locator("#id_name").fill("New Name")
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('storage-detail', kwargs={'pk': storage.pk})}")
    assert "New Name" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_delete_storage_when_multiple_exist(
    live_server, page, login, user, storage_factory
):
    storage_factory(user=user, name="Keep Me")
    doomed = storage_factory(user=user, name="Delete Me")
    login(user)
    page.goto(f"{live_server.url}{reverse('storage-delete', kwargs={'pk': doomed.pk})}")

    page.get_by_role("button", name="Delete").click()
    page.wait_for_url(f"**{reverse('storage-list')}")
    assert "Delete Me" not in page.locator("main").inner_text()
    assert "Keep Me" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_cannot_delete_the_last_storage(live_server, page, login, user):
    # A "Default Shelf" storage is auto-created for every new user
    # (wine_cellar/apps/storage/signals.py's post_save receiver on User) -
    # that's already the user's only storage, no need to create another.
    from wine_cellar.apps.storage.models import Storage

    only = Storage.objects.get(user=user)
    login(user)
    page.goto(f"{live_server.url}{reverse('storage-delete', kwargs={'pk': only.pk})}")

    page.get_by_role("button", name="Delete").click()
    page.wait_for_timeout(300)

    assert "at least one storage" in page.locator("main").inner_text()
    assert Storage.objects.filter(pk=only.pk).exists()


@pytest.mark.django_db
def test_grid_order_flips_with_swap_axes(
    live_server, page, login, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=2, columns=2, swap_axes=False)
    wine_a = wine_factory(user=user, name="Row1Col2")
    storage_item_factory(
        storage=storage, vintage=wine_a.latest_vintage, user=user, row=1, column=2
    )
    login(user)

    # `th` is styled `text-transform: uppercase`, which `innerText` reflects
    # (unlike `textContent`) - compare case-insensitively.
    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )
    headers = [
        h.upper() for h in page.locator("table.card__table thead th").all_inner_texts()
    ]
    assert headers.index("ROW") < headers.index("COLUMN")

    storage.swap_axes = True
    storage.save()
    page.reload()
    headers = [
        h.upper() for h in page.locator("table.card__table thead th").all_inner_texts()
    ]
    assert headers.index("COLUMN") < headers.index("ROW")


@pytest.mark.django_db
def test_naming_links_only_shown_when_axis_has_size_and_labels_enabled(
    live_server, page, login, user, storage_factory
):
    storage = storage_factory(
        user=user,
        rows=3,
        columns=0,
        row_labels_enabled=True,
        column_labels_enabled=True,
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )

    assert page.get_by_role("link", name="Name Rows").count() == 1
    # columns == 0, so there's nothing to name even though labels are enabled
    assert page.get_by_role("link", name="Name Columns").count() == 0

    storage.row_labels_enabled = False
    storage.save()
    page.reload()
    assert page.get_by_role("link", name="Name Rows").count() == 0
