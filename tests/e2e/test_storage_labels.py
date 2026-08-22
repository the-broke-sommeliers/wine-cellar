"""StorageLabelsView (wine_cellar/apps/storage/views.py:180-249,
storage_labels.html) - naming individual rows/columns, paginated 25 per
page, with an explicit invariant that saving one page/axis must never
touch another page's or the other axis's labels."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


def labels_url(live_server, pk, axis):
    path = reverse("storage-labels", kwargs={"pk": pk, "axis": axis})
    return f"{live_server.url}{path}"


@pytest.mark.django_db
def test_naming_rows_persists_and_shows_in_grid(
    live_server, page, login, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=3, columns=2)
    wine = wine_factory(user=user, name="Labeled Wine")
    storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, user=user, row=1, column=1
    )
    login(user)

    page.goto(labels_url(live_server, storage.pk, "row"))
    page.locator("input[name='row_1']").fill("Top Shelf")
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(
        f"**{reverse('storage-labels', kwargs={'pk': storage.pk, 'axis': 'row'})}**"
    )
    assert page.locator("input[name='row_1']").input_value() == "Top Shelf"

    page.goto(
        f"{live_server.url}{reverse('storage-detail', kwargs={'pk': storage.pk})}"
    )
    assert "Top Shelf" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_blanking_a_label_removes_it(live_server, page, login, user, storage_factory):
    storage = storage_factory(user=user, rows=2, columns=1)
    login(user)
    url = labels_url(live_server, storage.pk, "row")

    page.goto(url)
    page.locator("input[name='row_1']").fill("Named")
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(300)
    assert page.locator("input[name='row_1']").input_value() == "Named"

    page.locator("input[name='row_1']").fill("")
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(300)
    assert page.locator("input[name='row_1']").input_value() == ""

    from wine_cellar.apps.storage.models import StorageLabel

    assert not StorageLabel.objects.filter(
        storage=storage, axis="row", index=1
    ).exists()


@pytest.mark.django_db
def test_page_and_axis_isolation(live_server, page, login, user, storage_factory):
    """The view's own docstring states the invariant this covers: saving
    one page/axis must never delete or blank out labels belonging to a
    different page or axis."""
    storage = storage_factory(user=user, rows=30, columns=5)
    login(user)
    row_url = labels_url(live_server, storage.pk, "row")

    page.goto(row_url)
    page.locator("input[name='row_1']").fill("Page1 Row")
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(300)

    page.goto(f"{row_url}?page=2")
    page.locator("input[name='row_26']").fill("Page2 Row")
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(300)

    # Page 1 must still show its own label, untouched by page 2's save.
    page.goto(row_url)
    assert page.locator("input[name='row_1']").input_value() == "Page1 Row"

    # Naming a column must not touch the row labels either.
    column_url = labels_url(live_server, storage.pk, "column")
    page.goto(column_url)
    page.locator("input[name='column_1']").fill("A Column")
    page.get_by_role("button", name="Save").click()
    page.wait_for_timeout(300)

    page.goto(row_url)
    assert page.locator("input[name='row_1']").input_value() == "Page1 Row"
    page.goto(f"{row_url}?page=2")
    assert page.locator("input[name='row_26']").input_value() == "Page2 Row"
