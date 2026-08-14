from http import HTTPStatus

import pytest
from django.urls import reverse

from wine_cellar.apps.storage.models import Storage, StorageLabel

# ---------------------------------------------------------------------------
# StorageDetailView - swap_axes display ordering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_storage_detail_default_order_is_row_major(
    client,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    a = storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)
    b = storage_item_factory(storage=storage, wine=wine, row=2, column=1, user=user)
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["swap_axes"] is False
    positions = [
        entry.pk for entry in r.context["object_list"] if not isinstance(entry, dict)
    ]
    assert positions.index(a.pk) < positions.index(b.pk)


@pytest.mark.django_db
def test_storage_detail_swap_axes_orders_column_major(
    client,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2, swap_axes=True)
    wine = wine_factory(user=user)
    # A is at (2, 1), B is at (1, 2): row-major puts B first, column-major puts A first
    a = storage_item_factory(storage=storage, wine=wine, row=2, column=1, user=user)
    b = storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["swap_axes"] is True
    positions = [
        entry.pk for entry in r.context["object_list"] if not isinstance(entry, dict)
    ]
    assert positions.index(a.pk) < positions.index(b.pk)


@pytest.mark.django_db
def test_storage_detail_attaches_labels(
    client,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    storage_label_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_label_factory(storage=storage, axis="row", index=1, name="Spain")
    storage_label_factory(storage=storage, axis="column", index=2, name="Cheap")
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    assert r.status_code == HTTPStatus.OK
    item = next(
        entry for entry in r.context["object_list"] if not isinstance(entry, dict)
    )
    assert item.row_label == "Spain"
    assert item.column_label == "Cheap"


@pytest.mark.django_db
def test_storage_detail_shows_both_axis_labels_regardless_of_swap_axes(
    client,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    storage_label_factory,
    django_assert_num_queries,
):
    """Both axes can be independently named and shown at once - swap_axes
    only controls which column prints first, not which label(s) render."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_label_factory(storage=storage, axis="row", index=1, name="Spain")
    storage_label_factory(storage=storage, axis="column", index=2, name="Cheap")
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)

    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "(Spain)" in content
    assert "(Cheap)" in content

    storage.swap_axes = True
    storage.save()
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "(Spain)" in content
    assert "(Cheap)" in content


@pytest.mark.django_db
def test_storage_detail_hides_label_text_when_axis_disabled(
    client,
    user,
    wine_factory,
    storage_factory,
    storage_item_factory,
    storage_label_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2, row_labels_enabled=False)
    storage_label_factory(storage=storage, axis="row", index=1, name="Spain")
    storage_label_factory(storage=storage, axis="column", index=2, name="Cheap")
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)

    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "(Spain)" not in content
    assert "(Cheap)" in content
    # the underlying label is untouched, only the display is suppressed
    item = next(
        entry for entry in r.context["object_list"] if not isinstance(entry, dict)
    )
    assert item.row_label == "Spain"


@pytest.mark.django_db
def test_storage_detail_shows_both_naming_links_by_default(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" in content
    assert "Name Columns" in content


@pytest.mark.django_db
def test_storage_detail_naming_links_ignore_swap_axes(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2, swap_axes=True)
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" in content
    assert "Name Columns" in content


@pytest.mark.django_db
def test_storage_detail_hides_row_link_when_row_labels_disabled(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2, row_labels_enabled=False)
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" not in content
    assert "Name Columns" in content


@pytest.mark.django_db
def test_storage_detail_hides_column_link_when_column_labels_disabled(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2, column_labels_enabled=False)
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" in content
    assert "Name Columns" not in content


@pytest.mark.django_db
def test_storage_detail_hides_both_links_when_both_disabled(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(
        user=user,
        rows=2,
        columns=2,
        row_labels_enabled=False,
        column_labels_enabled=False,
    )
    with django_assert_num_queries(10):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" not in content
    assert "Name Columns" not in content


@pytest.mark.django_db
def test_storage_detail_shows_row_link_when_columns_zero(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=0)
    with django_assert_num_queries(8):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" in content
    assert "Name Columns" not in content


@pytest.mark.django_db
def test_storage_detail_shows_column_link_when_rows_zero(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=0, columns=2)
    with django_assert_num_queries(8):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" not in content
    assert "Name Columns" in content


@pytest.mark.django_db
def test_storage_detail_no_naming_link_without_grid(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=0, columns=0)
    with django_assert_num_queries(8):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    content = r.content.decode()
    assert "Name Rows" not in content
    assert "Name Columns" not in content


# ---------------------------------------------------------------------------
# StorageLabelsView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_storage_labels_get_row_screen(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=3)
    with django_assert_num_queries(4):
        r = client.get(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"})
        )
    assert r.status_code == HTTPStatus.OK
    assert r.context["axis"] == "row"
    assert r.context["entries"] == [(1, ""), (2, "")]


@pytest.mark.django_db
def test_storage_labels_get_column_screen(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=3)
    with django_assert_num_queries(4):
        r = client.get(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "column"})
        )
    assert r.status_code == HTTPStatus.OK
    assert r.context["axis"] == "column"
    assert r.context["entries"] == [(1, ""), (2, ""), (3, "")]


@pytest.mark.django_db
def test_storage_labels_get_invalid_axis(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    with django_assert_num_queries(2):
        r = client.get(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "diagonal"})
        )
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_storage_labels_get_disabled_axis_404(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2, row_labels_enabled=False)
    with django_assert_num_queries(3):
        r = client.get(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"})
        )
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_storage_labels_post_disabled_axis_404(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2, column_labels_enabled=False)
    with django_assert_num_queries(3):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "column"}),
            data={"column_1": "Cheap"},
        )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert storage.column_labels == {}


@pytest.mark.django_db
def test_storage_labels_create(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    data = {"row_1": "Spain"}
    with django_assert_num_queries(12):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            data=data,
        )
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == (
        reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}) + "?page=1"
    )
    assert storage.row_labels == {1: "Spain"}


@pytest.mark.django_db
def test_storage_labels_update(
    client, user, storage_factory, storage_label_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_label_factory(storage=storage, axis="row", index=1, name="Old Name")
    data = {"row_1": "New Name"}
    with django_assert_num_queries(10):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            data=data,
        )
    assert r.status_code == HTTPStatus.FOUND
    assert StorageLabel.objects.count() == 1
    assert storage.row_labels == {1: "New Name"}


@pytest.mark.django_db
def test_storage_labels_blank_deletes(
    client, user, storage_factory, storage_label_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_label_factory(storage=storage, axis="row", index=1, name="Spain")
    data = {"row_1": ""}
    with django_assert_num_queries(7):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            data=data,
        )
    assert r.status_code == HTTPStatus.FOUND
    assert StorageLabel.objects.count() == 0


@pytest.mark.django_db
def test_storage_labels_saving_rows_does_not_touch_columns(
    client, user, storage_factory, storage_label_factory, django_assert_num_queries
):
    """Regression: the dedicated screen only ever submits fields for its own
    axis - saving rows must not wipe out existing column labels, and vice
    versa."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_label_factory(storage=storage, axis="column", index=1, name="Cheap")
    data = {"row_1": "Spain"}
    with django_assert_num_queries(12):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            data=data,
        )
    assert r.status_code == HTTPStatus.FOUND
    assert storage.row_labels == {1: "Spain"}
    assert storage.column_labels == {1: "Cheap"}


@pytest.mark.django_db
def test_storage_labels_saving_columns_does_not_touch_rows(
    client, user, storage_factory, storage_label_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_label_factory(storage=storage, axis="row", index=1, name="Spain")
    data = {"column_1": "Cheap"}
    with django_assert_num_queries(12):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "column"}),
            data=data,
        )
    assert r.status_code == HTTPStatus.FOUND
    assert storage.row_labels == {1: "Spain"}
    assert storage.column_labels == {1: "Cheap"}


@pytest.mark.django_db
def test_storage_labels_post_invalid_axis(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    with django_assert_num_queries(2):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "diagonal"}),
            data={},
        )
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_storage_labels_unauthenticated(
    client, storage_factory, django_assert_num_queries
):
    storage = storage_factory()
    url = reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"})
    with django_assert_num_queries(0):
        r = client.post(url, data={})
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == reverse("account_login") + "?next=" + url


@pytest.mark.django_db
def test_storage_labels_other_user(
    client, user, user_factory, storage_factory, django_assert_num_queries
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=other, rows=2, columns=2)
    with django_assert_num_queries(3):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            data={"row_1": "Spain"},
        )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert Storage.objects.get(pk=storage.pk).row_labels == {}


# ---------------------------------------------------------------------------
# StorageLabelsView - pagination
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_storage_labels_get_paginates_at_25(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=60, columns=1)
    with django_assert_num_queries(4):
        r = client.get(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"})
        )
    assert r.status_code == HTTPStatus.OK
    assert len(r.context["entries"]) == 25
    assert r.context["entries"][0][0] == 1
    assert r.context["entries"][-1][0] == 25
    assert r.context["page_obj"].number == 1
    assert r.context["page_obj"].paginator.num_pages == 3


@pytest.mark.django_db
def test_storage_labels_get_page_2_returns_next_slice(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=60, columns=1)
    with django_assert_num_queries(4):
        r = client.get(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            {"page": 2},
        )
    assert r.status_code == HTTPStatus.OK
    assert [index for index, _ in r.context["entries"]] == list(range(26, 51))


@pytest.mark.django_db
def test_storage_labels_get_out_of_range_page_clamps_to_last(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=60, columns=1)
    with django_assert_num_queries(4):
        r = client.get(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            {"page": 999},
        )
    assert r.status_code == HTTPStatus.OK
    assert r.context["page_obj"].number == 3
    assert [index for index, _ in r.context["entries"]] == list(range(51, 61))


@pytest.mark.django_db
def test_storage_labels_post_page_isolation_does_not_touch_other_pages(
    client, user, storage_factory, storage_label_factory, django_assert_num_queries
):
    """The critical regression this pagination change must not reintroduce:
    saving one page must never blank/delete labels on a different page."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=60, columns=1)
    storage_label_factory(storage=storage, axis="row", index=1, name="Page 1 Label")
    storage_label_factory(storage=storage, axis="row", index=30, name="Old Name")

    with django_assert_num_queries(33):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            data={"page": "2", "row_30": "Renamed"},
        )
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == (
        reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}) + "?page=2"
    )
    assert storage.row_labels[1] == "Page 1 Label"
    assert storage.row_labels[30] == "Renamed"


@pytest.mark.django_db
def test_storage_labels_post_blank_on_page_only_deletes_within_that_page(
    client, user, storage_factory, storage_label_factory, django_assert_num_queries
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=60, columns=1)
    storage_label_factory(storage=storage, axis="row", index=1, name="Page 1 Label")
    storage_label_factory(storage=storage, axis="row", index=26, name="Page 2 Label")

    with django_assert_num_queries(30):
        r = client.post(
            reverse("storage-labels", kwargs={"pk": storage.pk, "axis": "row"}),
            data={"page": "2", "row_26": ""},
        )
    assert r.status_code == HTTPStatus.FOUND
    assert storage.row_labels == {1: "Page 1 Label"}
