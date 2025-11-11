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
    r = client.post(reverse("stock-add", kwargs={"pk": wine.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("stock-add", kwargs={"pk": wine.pk}),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_user_can_add_stock(client, user, wine_factory):
    client.force_login(user)
    storage = Storage.objects.first()
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 1
    assert storage.items.first().wine == wine


@pytest.mark.django_db
def test_user_cant_add_stock_to_other_users_storage(
    client, user, user_factory, wine_factory
):
    storage = Storage.objects.filter(user=user).first()
    other_user = user_factory()
    other_storage = Storage.objects.filter(user=other_user).first()
    client.force_login(user)
    wine = wine_factory(user=user)
    other_wine = wine_factory(user=other_user)
    data = {
        "storage": other_storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert other_storage.used_slots == 0
    r = client.post(
        reverse("stock-add", kwargs={"pk": other_wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert other_storage.used_slots == 0
    assert StorageItem.objects.count() == 0
    data = {
        "storage": storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": other_wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert other_storage.used_slots == 0
    assert StorageItem.objects.count() == 0


@pytest.mark.django_db
def test_user_can_delete_stock(client, user, wine_factory, storage_item_factory):
    client.force_login(user)
    storage = Storage.objects.first()
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
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
    item = storage_item_factory(storage=storage, wine=wine, user=user2)
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
    storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": storage.pk,
        "row": 1,
        "column": 1,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
def test_user_can_add_to_specific_slot(client, user, storage_factory, wine_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "row": 2,
        "column": 1,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    item = storage.items.first()
    assert item.wine == wine
    assert item.row == 2
    assert item.column == 1


@pytest.mark.django_db
def test_user_cant_add_to_invalid_slot(client, user, storage_factory, wine_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "row": 3,
        "column": 1,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
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
    r = client.get(reverse("stock-add", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["free_cells_by_storage"][storage.pk] == {
        1: [1, 2],
        2: [1, 2],
    }
    storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    storage_item_factory(storage=storage, wine=wine, row=2, column=2, user=user)
    r = client.get(reverse("stock-add", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["free_cells_by_storage"][storage.pk] == {
        1: [2],
        2: [1],
    }
