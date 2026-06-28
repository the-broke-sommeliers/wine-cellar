from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateUsed,
)

from wine_cellar.apps.storage.models import Storage, StorageItem


@pytest.mark.django_db
def test_storage_create_page_unauthenticated(client, user):
    r = client.get(reverse("storage-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login") + "?next=" + reverse("storage-add"),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_storage_create_page(client, user):
    client.force_login(user)
    r = client.get(reverse("storage-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="storage_create.html")


@pytest.mark.django_db
def test_storage_create_post_empty(client, user):
    client.force_login(user)
    data = {}
    r = client.post(reverse("storage-add"), data)
    assert r.status_code == HTTPStatus.OK
    f = r.context["form"]
    assert not f.is_valid()
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="storage_create.html")
    assert Storage.objects.count() == 1


@pytest.mark.django_db
def test_storage_create_post_unauthenticated(client, user):
    r = client.post(reverse("storage-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login") + "?next=" + reverse("storage-add"),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")
    assert Storage.objects.count() == 1


@pytest.mark.django_db
def test_storage_create_post(client, user):
    client.force_login(user)
    data = {
        "name": "Shelf 1",
        "location": "Basement",
        "rows": 5,
        "columns": 10,
    }

    assert Storage.objects.count() == 1
    r = client.post(reverse("storage-add"), data=data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("storage-list"))
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="storage_list.html")
    assert Storage.objects.count() == 2
    storage = Storage.objects.last()
    assert storage.user == user
    assert storage.name == data["name"]
    assert storage.location == data["location"]
    assert storage.rows == data["rows"]
    assert storage.columns == data["columns"]


@pytest.mark.django_db
def test_storage_create_post_invalid(client, user):
    client.force_login(user)
    data = {
        "name": "Merlot",
        "rows": 5,
        "columns": 10,
    }
    assert Storage.objects.count() == 1
    r = client.get(reverse("storage-add"))
    r = client.post(reverse("storage-add"), data=data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors


@pytest.mark.django_db
def test_storage_cant_edit_other_users(client, user, user_factory, storage_factory):
    other_user = user_factory()
    storage_other_user = storage_factory(user=other_user)
    client.force_login(user)
    assert Storage.objects.count() == 3
    r = client.post(
        reverse("storage-edit", kwargs={"pk": storage_other_user.pk}), follow=True
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_storage_update_post(client, user):
    client.force_login(user)
    storage = Storage.objects.first()
    data = {
        "name": storage.name,
        "location": "Basement",
        "rows": 1,
        "columns": 10,
    }
    assert Storage.objects.count() == 1
    r = client.post(
        reverse("storage-edit", kwargs={"pk": storage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("storage-detail", kwargs={"pk": storage.pk})
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="storage_detail.html")
    storage.refresh_from_db()
    assert storage.user == user
    assert storage.rows == data["rows"]
    assert storage.columns == data["columns"]


@pytest.mark.django_db
def test_storage_cant_delete_only(client, user):
    client.force_login(user)
    assert Storage.objects.count() == 1
    storage = Storage.objects.first()
    r = client.post(reverse("storage-delete", kwargs={"pk": storage.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors


@pytest.mark.django_db
def test_storage_cant_delete_other_users(client, user, user_factory, storage_factory):
    other_user = user_factory()
    storage_other_user = storage_factory(user=other_user)
    client.force_login(user)
    assert Storage.objects.count() == 3
    r = client.post(
        reverse("storage-delete", kwargs={"pk": storage_other_user.pk}), follow=True
    )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert Storage.objects.count() == 3


@pytest.mark.django_db
def test_storage_can_delete_multiple(client, user, storage_factory):
    client.force_login(user)
    storage_factory(user=user)
    assert Storage.objects.count() == 2
    storage = Storage.objects.first()
    r = client.post(reverse("storage-delete", kwargs={"pk": storage.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("storage-list"))
    assert Storage.objects.count() == 1


@pytest.mark.django_db
def test_unauthenticated_cant_add_stock(client, user, wine_factory):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    r = client.post(reverse("stock-add", kwargs={"pk": vintage.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("stock-add", kwargs={"pk": vintage.pk}),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_user_can_add_stock(client, user, wine_factory):
    client.force_login(user)
    storage = Storage.objects.first()
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    data = {
        "storage": storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": vintage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 1
    assert storage.items.first().vintage.wine == wine


@pytest.mark.django_db
def test_user_cant_add_stock_to_other_users_storage(
    client, user, user_factory, wine_factory
):
    storage = Storage.objects.filter(user=user).first()
    other_user = user_factory()
    other_storage = Storage.objects.filter(user=other_user).first()
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    other_wine = wine_factory(user=other_user)
    other_vintage = other_wine.latest_vintage
    data = {
        "storage": other_storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": vintage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert other_storage.used_slots == 0
    r = client.post(
        reverse("stock-add", kwargs={"pk": other_vintage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert other_storage.used_slots == 0
    assert StorageItem.objects.count() == 0
    data = {
        "storage": storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": other_vintage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert other_storage.used_slots == 0
    assert StorageItem.objects.count() == 0


@pytest.mark.django_db
def test_user_can_delete_stock(client, user, wine_factory, storage_item_factory):
    client.force_login(user)
    storage = Storage.objects.first()
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    item = storage_item_factory(storage=storage, vintage=vintage, user=user)
    assert item.deleted is False
    assert StorageItem.objects.count() == 1
    r = client.post(reverse("stock-delete", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert StorageItem.objects.count() == 1
    item.refresh_from_db()
    assert item.deleted is True


@pytest.mark.django_db
def test_user_cant_delete_other_users_stock(
    client, user, user_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    user2 = user_factory()
    storage = Storage.objects.filter(user=user2).first()
    wine = wine_factory(user=user2)
    vintage = wine.latest_vintage
    item = storage_item_factory(storage=storage, vintage=vintage, user=user2)
    assert item.deleted is False
    assert StorageItem.objects.count() == 1
    r = client.post(reverse("stock-delete", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert StorageItem.objects.count() == 1
    item.refresh_from_db()
    assert item.deleted is False


@pytest.mark.django_db
def test_user_cant_add_to_full_slot(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=1, columns=1)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    storage_item_factory(storage=storage, vintage=vintage, row=1, column=1, user=user)
    data = {
        "storage": storage.pk,
        "row": 1,
        "column": 1,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": vintage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
def test_user_can_add_to_specific_slot(client, user, storage_factory, wine_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    data = {
        "storage": storage.pk,
        "row": 2,
        "column": 1,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": vintage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    item = storage.items.first()
    assert item.vintage.wine == wine
    assert item.row == 2
    assert item.column == 1


@pytest.mark.django_db
def test_user_cant_add_to_invalid_slot(client, user, storage_factory, wine_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    data = {
        "storage": storage.pk,
        "row": 3,
        "column": 1,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": vintage.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
def test_form_context_has_empty_slots(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    r = client.get(reverse("stock-add", kwargs={"pk": vintage.pk}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["free_cells_by_storage"][storage.pk] == {
        1: [1, 2],
        2: [1, 2],
    }
    storage_item_factory(storage=storage, vintage=vintage, row=1, column=1, user=user)
    storage_item_factory(storage=storage, vintage=vintage, row=2, column=2, user=user)
    r = client.get(reverse("stock-add", kwargs={"pk": vintage.pk}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["free_cells_by_storage"][storage.pk] == {
        1: [2],
        2: [1],
    }


@pytest.mark.django_db
def test_used_slot_is_free_after_delete(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    wine_new = wine_factory(user=user)
    vintage_new = wine_new.latest_vintage
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user, deleted=True
    )
    client.force_login(user)
    data = {
        "storage": storage.pk,
        "row": 1,
        "column": 1,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": vintage_new.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine_new.pk})
    )
    item = storage.items.filter(deleted=False).first()
    assert item.vintage.wine == wine_new
    assert item.row == 1
    assert item.column == 1
    assert item.deleted is False


@pytest.mark.django_db
def test_user_can_edit_existing_item_new_slot(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    item = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user
    )
    data = {
        "storage": storage.pk,
        "row": 2,
        "column": 1,
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 1
    assert storage.items.first().vintage.wine == wine
    item = storage.items.first()
    assert item.vintage.wine == wine
    assert item.row == 2
    assert item.column == 1


@pytest.mark.django_db
def test_user_can_edit_existing_item_new_price(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    item = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user, price=10.0
    )
    data = {
        "storage": storage.pk,
        "row": 1,
        "column": 1,
        "price": 15.0,
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 1
    assert storage.items.first().vintage.wine == wine
    item = storage.items.first()
    assert item.vintage.wine == wine
    assert item.row == 1
    assert item.column == 1
    assert item.price == 15.0


@pytest.mark.django_db
def test_user_cant_edit_to_occupied_slot(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    item = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user
    )
    storage_item_factory(
        storage=storage,
        vintage=wine_factory(user=user).latest_vintage,
        row=2,
        column=1,
        user=user,
    )
    data = {
        "storage": storage.pk,
        "row": 2,
        "column": 1,
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
def test_stock_swap_success(
    client, user, storage_factory, wine_factory, storage_item_factory
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
    vintage = wine.latest_vintage
    item1 = storage_item_factory(
        storage=storage1, vintage=vintage, row=1, column=1, user=user
    )
    item2 = storage_item_factory(
        storage=storage2, vintage=vintage, row=2, column=2, user=user
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
    vintage = wine.latest_vintage
    # A@(1,1)  B@(1,2)  C@(1,3)  D@(1,4)
    a = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user
    )
    b = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=2, user=user
    )
    c = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=3, user=user
    )
    d = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=4, user=user
    )
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
    vintage = wine.latest_vintage
    # A@(1,1)  B@(1,2)  C@(1,3)  D@(1,4)
    a = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user
    )
    b = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=2, user=user
    )
    c = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=3, user=user
    )
    d = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=4, user=user
    )
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
    vintage = wine.latest_vintage
    item = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user
    )
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
    vintage = wine.latest_vintage
    item = storage_item_factory(
        storage=storage1, vintage=vintage, row=1, column=1, user=user
    )
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
    vintage = wine.latest_vintage
    item1 = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user
    )
    storage_item_factory(storage=storage, vintage=vintage, row=1, column=2, user=user)
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
    vintage = wine.latest_vintage
    item1 = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=other
    )
    item2 = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=2, user=other
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
    vintage = wine.latest_vintage
    item1 = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user, deleted=True
    )
    item2 = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=2, user=user
    )
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


@pytest.mark.django_db
def test_user_cant_edit_to_other_users_storage(
    client, user, user_factory, storage_factory, wine_factory, storage_item_factory
):
    other_user = user_factory()
    other_storage = Storage.objects.filter(user=other_user).first()
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    item = storage_item_factory(
        storage=storage, vintage=vintage, row=1, column=1, user=user
    )
    data = {
        "storage": other_storage.pk,
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
