from http import HTTPStatus

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_stock_swap_success(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    wine1 = wine_factory(user=user)
    wine2 = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage, wine=wine1, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage, wine=wine2, row=1, column=2, user=user
    )
    data = {"item1": item1.pk, "item2": item2.pk}
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
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage1 = storage_factory(user=user, rows=2, columns=2)
    storage2 = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage1, wine=wine, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage2, wine=wine, row=2, column=2, user=user
    )
    data = {"item1": item1.pk, "item2": item2.pk}
    r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json()["ok"] is False


@pytest.mark.django_db
def test_stock_swap_chain_shift_forward(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    """Non-adjacent forward: items between old and new shift backward, no gaps."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=4)
    wine = wine_factory(user=user)
    # A@(1,1)  B@(1,2)  C@(1,3)  D@(1,4)
    a = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    b = storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)
    c = storage_item_factory(storage=storage, wine=wine, row=1, column=3, user=user)
    d = storage_item_factory(storage=storage, wine=wine, row=1, column=4, user=user)
    # Move A from (1,1) to (1,4): B,C,D shift backward to fill gap
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
    client, user, storage_factory, wine_factory, storage_item_factory
):
    """Non-adjacent backward: items between new and old shift forward, no gaps."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=4)
    wine = wine_factory(user=user)
    # A@(1,1)  B@(1,2)  C@(1,3)  D@(1,4)
    a = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    b = storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)
    c = storage_item_factory(storage=storage, wine=wine, row=1, column=3, user=user)
    d = storage_item_factory(storage=storage, wine=wine, row=1, column=4, user=user)
    # Move D from (1,4) to (1,1): A,B,C shift forward to fill gap at (1,4)
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
    client, user, storage_factory, wine_factory, storage_item_factory
):
    """Dropping on an empty slot just moves the item, no shift."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=3)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "item1": item.pk,
        "storage": storage.pk,
        "row": 1,
        "column": 3,
    }
    r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.OK
    item.refresh_from_db()
    assert item.row == 1
    assert item.column == 3


@pytest.mark.django_db
def test_stock_move_to_empty_slot_cross_storage_rejected(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    """Dropping on an empty slot in another storage is rejected."""
    client.force_login(user)
    storage1 = storage_factory(user=user, rows=1, columns=3)
    storage2 = storage_factory(user=user, rows=1, columns=3)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage1, wine=wine, row=1, column=1, user=user)
    data = {
        "item1": item.pk,
        "storage": storage2.pk,
        "row": 1,
        "column": 2,
    }
    r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_stock_move_to_occupied_slot_rejected(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    """Dropping on an occupied slot via empty-slot params is rejected."""
    client.force_login(user)
    storage = storage_factory(user=user, rows=1, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)
    data = {
        "item1": item1.pk,
        "storage": storage.pk,
        "row": 1,
        "column": 2,
    }
    r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_stock_swap_unauthenticated(client, storage_item_factory):
    item1 = storage_item_factory()
    item2 = storage_item_factory()
    data = {"item1": item1.pk, "item2": item2.pk}
    r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == reverse("account_login") + "?next=" + reverse("stock-swap")


@pytest.mark.django_db
def test_stock_swap_other_user(
    client, user, user_factory, storage_factory, wine_factory, storage_item_factory
):
    other = user_factory()
    client.force_login(user)
    storage = storage_factory(user=other, rows=2, columns=2)
    wine = wine_factory(user=other)
    item1 = storage_item_factory(
        storage=storage, wine=wine, row=1, column=1, user=other
    )
    item2 = storage_item_factory(
        storage=storage, wine=wine, row=1, column=2, user=other
    )
    data = {"item1": item1.pk, "item2": item2.pk}
    r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_stock_swap_deleted_item(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    item1 = storage_item_factory(
        storage=storage, wine=wine, row=1, column=1, user=user, deleted=True
    )
    item2 = storage_item_factory(storage=storage, wine=wine, row=1, column=2, user=user)
    data = {"item1": item1.pk, "item2": item2.pk}
    r = client.post(reverse("stock-swap"), data=data)
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_stock_swap_missing_params(client, user):
    client.force_login(user)
    r = client.post(reverse("stock-swap"), data={})
    assert r.status_code == HTTPStatus.NOT_FOUND
    r = client.post(reverse("stock-swap"), data={"item1": 1})
    assert r.status_code == HTTPStatus.NOT_FOUND
