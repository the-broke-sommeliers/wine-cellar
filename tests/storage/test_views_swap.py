from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse

from wine_cellar.apps.storage.models import StorageItem


@pytest.mark.django_db
def test_stock_swap_success(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    wine1 = wine_factory(user=user)
    wine2 = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage, vintage=wine1.latest_vintage, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage, vintage=wine2.latest_vintage, row=1, column=2, user=user
    )
    data = {"item1": item1.pk, "item2": item2.pk}
    with django_assert_num_queries(12):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.OK
    assert r.json() == {"ok": True}
    item1.refresh_from_db()
    item2.refresh_from_db()
    # Adjacent cells: simple swap
    assert item1.row == 1
    assert item1.column == 2
    assert item2.row == 1
    assert item2.column == 1


@pytest.mark.django_db
def test_stock_swap_cross_storage_rejected(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage1 = storage_factory(user=user, rows=2, columns=2)
    storage2 = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage1, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage2, vintage=wine.latest_vintage, row=2, column=2, user=user
    )
    data = {"item1": item1.pk, "item2": item2.pk}
    with django_assert_num_queries(4):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json()["ok"] is False


@pytest.mark.django_db
def test_stock_swap_chain_shift_forward(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Non-adjacent forward: items between old and new shift backward, no gaps."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=4)
    wine = wine_factory(user=user)
    # A@(1,1)  B@(1,2)  C@(1,3)  D@(1,4)
    a = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    b = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )
    c = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=3, user=user
    )
    d = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=4, user=user
    )
    # Move A from (1,1) to (1,4): B,C,D shift backward to fill gap
    with django_assert_num_queries(14):
        r = client.post(
            reverse("stock-swap"),
            data={"item1": a.pk, "item2": d.pk},
        )
    assert r.status_code == HTTPStatus.OK
    a.refresh_from_db()
    b.refresh_from_db()
    c.refresh_from_db()
    d.refresh_from_db()
    assert a.row == 1 and a.column == 4
    assert b.row == 1 and b.column == 1
    assert c.row == 1 and c.column == 2
    assert d.row == 1 and d.column == 3


@pytest.mark.django_db
def test_stock_swap_chain_shift_backward(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Non-adjacent backward: items between new and old shift forward, no gaps."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=4)
    wine = wine_factory(user=user)
    # A@(1,1)  B@(1,2)  C@(1,3)  D@(1,4)
    a = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    b = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )
    c = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=3, user=user
    )
    d = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=4, user=user
    )
    # Move D from (1,4) to (1,1): A,B,C shift forward to fill gap at (1,4)
    with django_assert_num_queries(14):
        r = client.post(
            reverse("stock-swap"),
            data={"item1": d.pk, "item2": a.pk},
        )
    assert r.status_code == HTTPStatus.OK
    a.refresh_from_db()
    b.refresh_from_db()
    c.refresh_from_db()
    d.refresh_from_db()
    assert d.row == 1 and d.column == 1
    assert a.row == 1 and a.column == 2
    assert b.row == 1 and b.column == 3
    assert c.row == 1 and c.column == 4


@pytest.mark.django_db
def test_stock_move_to_empty_slot(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Dropping on an empty slot just moves the item, no shift."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=3)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    data = {
        "item1": item.pk,
        "storage": storage.pk,
        "row": 1,
        "column": 3,
    }
    with django_assert_num_queries(11):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.OK
    item.refresh_from_db()
    assert item.row == 1
    assert item.column == 3


@pytest.mark.django_db
def test_stock_move_to_empty_slot_cross_storage_rejected(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Dropping on an empty slot in another storage is rejected."""
    client.force_login(user)
    storage1 = storage_factory(user=user, rows=1, columns=3)
    storage2 = storage_factory(user=user, rows=1, columns=3)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage1, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    data = {
        "item1": item.pk,
        "storage": storage2.pk,
        "row": 1,
        "column": 2,
    }
    with django_assert_num_queries(3):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_stock_move_to_occupied_slot_rejected(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Dropping on an occupied slot via empty-slot params is rejected."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )
    data = {
        "item1": item1.pk,
        "storage": storage.pk,
        "row": 1,
        "column": 2,
    }
    with django_assert_num_queries(10):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_stock_swap_unauthenticated(
    client, storage_item_factory, django_assert_num_queries
):
    item1 = storage_item_factory()
    item2 = storage_item_factory()
    data = {"item1": item1.pk, "item2": item2.pk}
    with django_assert_num_queries(0):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == reverse("account_login") + "?next=" + reverse("stock-swap")


@pytest.mark.django_db
def test_stock_swap_other_user(
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
    storage = storage_factory(user=other, rows=2, columns=2)
    wine = wine_factory(user=other)
    item1 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=other
    )
    item2 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=other
    )
    data = {"item1": item1.pk, "item2": item2.pk}
    with django_assert_num_queries(3):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_stock_swap_deleted_item(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage,
        vintage=wine.latest_vintage,
        row=1,
        column=1,
        user=user,
        deleted=True,
    )
    item2 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )
    data = {"item1": item1.pk, "item2": item2.pk}
    with django_assert_num_queries(3):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_stock_swap_missing_params(client, user, django_assert_num_queries):
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.post(reverse("stock-swap"), data={})
    assert r.status_code == HTTPStatus.NOT_FOUND
    with django_assert_num_queries(3):
        r = client.post(reverse("stock-swap"), data={"item1": 1})
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_stock_swap_source_deleted_mid_race_rejected(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Source is soft-deleted by another request between the initial fetch
    and the lock-then-recheck inside the transaction - must be rejected,
    not silently moved."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )

    original_refresh = StorageItem.refresh_from_db

    def fake_refresh(self, *args, **kwargs):
        original_refresh(self, *args, **kwargs)
        if self.pk == item1.pk:
            self.deleted = True

    with patch.object(StorageItem, "refresh_from_db", fake_refresh):
        with django_assert_num_queries(9):
            r = client.post(
                reverse("stock-swap"), data={"item1": item1.pk, "item2": item2.pk}
            )
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json() == {"ok": False, "error": "Slot is occupied."}


@pytest.mark.django_db
def test_stock_swap_target_deleted_mid_race_rejected(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Target is soft-deleted by another request between the initial fetch
    and the lock-then-recheck - must be rejected."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )

    original_refresh = StorageItem.refresh_from_db

    def fake_refresh(self, *args, **kwargs):
        original_refresh(self, *args, **kwargs)
        if self.pk == item2.pk:
            self.deleted = True

    with patch.object(StorageItem, "refresh_from_db", fake_refresh):
        with django_assert_num_queries(10):
            r = client.post(
                reverse("stock-swap"), data={"item1": item1.pk, "item2": item2.pk}
            )
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json() == {"ok": False, "error": "Slot is occupied."}


@pytest.mark.django_db
def test_stock_swap_target_moved_storage_mid_race_rejected(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Target is moved to a different storage by another request between
    the initial fetch and the lock-then-recheck - must be rejected."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=2)
    other_storage = storage_factory(user=user, rows=1, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )

    original_refresh = StorageItem.refresh_from_db

    def fake_refresh(self, *args, **kwargs):
        original_refresh(self, *args, **kwargs)
        if self.pk == item2.pk:
            self.storage_id = other_storage.pk

    with patch.object(StorageItem, "refresh_from_db", fake_refresh):
        with django_assert_num_queries(10):
            r = client.post(
                reverse("stock-swap"), data={"item1": item1.pk, "item2": item2.pk}
            )
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json() == {"ok": False, "error": "Slot is occupied."}


@pytest.mark.django_db
def test_stock_swap_unlimited_storage_defaults_to_zero_zero(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """For an unlimited storage (columns=0), the empty-slot move path skips
    all bounds/occupancy validation entirely (it's gated behind
    `storage.columns > 0`), and `new_row`/`new_col` default to 0 rather
    than staying None. This pins the current (likely unintended) behavior -
    worth revisiting if a real bug report surfaces here."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=0, columns=0)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=None, column=None, user=user
    )
    data = {"item1": item.pk, "storage": storage.pk}
    with django_assert_num_queries(10):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.OK
    item.refresh_from_db()
    assert (item.row, item.column) == (0, 0)


@pytest.mark.django_db
def test_stock_swap_out_of_bounds_slot_rejected(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Moving to an empty slot outside the grid's bounds is rejected."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    data = {"item1": item.pk, "storage": storage.pk, "row": 99, "column": 1}
    with django_assert_num_queries(4):
        r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json() == {"ok": False, "error": "Invalid slot."}


@pytest.mark.django_db
def test_stock_swap_chain_shift_spans_multiple_rows(
    client,
    user,
    storage_factory,
    wine_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Chain-shift where old and new positions are on different rows must
    use the multi-row range filter in `_shift_toward`, not just the
    single-row filter already covered by the same-row chain-shift tests."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    # Full grid, row-major: A@(1,1) B@(1,2) C@(2,1) D@(2,2)
    a = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=1, user=user
    )
    b = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=1, column=2, user=user
    )
    c = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=2, column=1, user=user
    )
    d = storage_item_factory(
        storage=storage, vintage=wine.latest_vintage, row=2, column=2, user=user
    )
    # Move A to D's slot: B, C, D each shift back one slot (wrapping across
    # the row boundary) to fill the gap left by A.
    with django_assert_num_queries(14):
        r = client.post(reverse("stock-swap"), data={"item1": a.pk, "item2": d.pk})
    assert r.status_code == HTTPStatus.OK
    a.refresh_from_db()
    b.refresh_from_db()
    c.refresh_from_db()
    d.refresh_from_db()
    assert (a.row, a.column) == (2, 2)
    assert (b.row, b.column) == (1, 1)
    assert (c.row, c.column) == (1, 2)
    assert (d.row, d.column) == (2, 1)
