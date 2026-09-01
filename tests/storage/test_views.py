from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateUsed,
)

from wine_cellar.apps.storage.models import Storage


@pytest.mark.django_db
def test_storage_create_page_unauthenticated(client, user, django_assert_num_queries):
    with django_assert_num_queries(1):
        r = client.get(reverse("storage-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login") + "?next=" + reverse("storage-add"),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_storage_create_page(client, user, django_assert_num_queries):
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.get(reverse("storage-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="storage_create.html")


@pytest.mark.django_db
def test_storage_create_post_empty(client, user, django_assert_num_queries):
    client.force_login(user)
    data = {}
    with django_assert_num_queries(3):
        r = client.post(reverse("storage-add"), data)
    assert r.status_code == HTTPStatus.OK
    f = r.context["form"]
    assert not f.is_valid()
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="storage_create.html")
    assert Storage.objects.count() == 1


@pytest.mark.django_db
def test_storage_create_post_unauthenticated(client, user, django_assert_num_queries):
    with django_assert_num_queries(1):
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
def test_storage_create_post(client, user, django_assert_num_queries):
    client.force_login(user)
    data = {
        "name": "Shelf 1",
        "location": "Basement",
        "rows": 5,
        "columns": 10,
    }

    assert Storage.objects.count() == 1
    with django_assert_num_queries(10):
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
def test_storage_create_post_swap_axes(client, user, django_assert_num_queries):
    client.force_login(user)
    data = {
        "name": "Shelf 1",
        "location": "Basement",
        "rows": 5,
        "columns": 10,
        "swap_axes": "on",
    }
    with django_assert_num_queries(10):
        r = client.post(reverse("storage-add"), data=data, follow=True)
    assert r.status_code == HTTPStatus.OK
    storage = Storage.objects.last()
    assert storage.swap_axes is True


@pytest.mark.django_db
def test_storage_create_post_row_labels_enabled(
    client, user, django_assert_num_queries
):
    client.force_login(user)
    data = {
        "name": "Shelf 1",
        "location": "Basement",
        "rows": 5,
        "columns": 10,
        "row_labels_enabled": "on",
    }
    with django_assert_num_queries(10):
        r = client.post(reverse("storage-add"), data=data, follow=True)
    assert r.status_code == HTTPStatus.OK
    storage = Storage.objects.last()
    assert storage.row_labels_enabled is True
    assert storage.column_labels_enabled is False


@pytest.mark.django_db
def test_storage_create_post_column_labels_enabled(
    client, user, django_assert_num_queries
):
    client.force_login(user)
    data = {
        "name": "Shelf 1",
        "location": "Basement",
        "rows": 5,
        "columns": 10,
        "column_labels_enabled": "on",
    }
    with django_assert_num_queries(10):
        r = client.post(reverse("storage-add"), data=data, follow=True)
    assert r.status_code == HTTPStatus.OK
    storage = Storage.objects.last()
    assert storage.column_labels_enabled is True
    assert storage.row_labels_enabled is False


@pytest.mark.django_db
def test_storage_create_post_invalid(client, user, django_assert_num_queries):
    client.force_login(user)
    data = {
        "name": "Merlot",
        "rows": 5,
        "columns": 10,
    }
    assert Storage.objects.count() == 1
    r = client.get(reverse("storage-add"))
    with django_assert_num_queries(2):
        r = client.post(reverse("storage-add"), data=data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors


@pytest.mark.django_db
def test_storage_cant_edit_other_users(
    client, user, user_factory, storage_factory, django_assert_num_queries
):
    other_user = user_factory()
    storage_other_user = storage_factory(user=other_user)
    client.force_login(user)
    assert Storage.objects.count() == 3
    with django_assert_num_queries(3):
        r = client.post(
            reverse("storage-edit", kwargs={"pk": storage_other_user.pk}), follow=True
        )
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_storage_update_post(client, user, django_assert_num_queries):
    client.force_login(user)
    storage = Storage.objects.first()
    data = {
        "name": storage.name,
        "location": "Basement",
        "rows": 1,
        "columns": 10,
    }
    assert Storage.objects.count() == 1
    with django_assert_num_queries(16):
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
def test_storage_update_post_swap_axes(client, user, django_assert_num_queries):
    client.force_login(user)
    storage = Storage.objects.first()
    data = {
        "name": storage.name,
        "location": "Basement",
        "rows": 1,
        "columns": 10,
        "swap_axes": "on",
    }
    with django_assert_num_queries(16):
        r = client.post(
            reverse("storage-edit", kwargs={"pk": storage.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    storage.refresh_from_db()
    assert storage.swap_axes is True

    data["swap_axes"] = ""
    with django_assert_num_queries(15):
        r = client.post(
            reverse("storage-edit", kwargs={"pk": storage.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    storage.refresh_from_db()
    assert storage.swap_axes is False


@pytest.mark.django_db
def test_storage_update_post_row_labels_enabled(
    client, user, django_assert_num_queries
):
    client.force_login(user)
    storage = Storage.objects.first()
    data = {
        "name": storage.name,
        "location": "Basement",
        "rows": 1,
        "columns": 10,
        "row_labels_enabled": "on",
    }
    with django_assert_num_queries(16):
        r = client.post(
            reverse("storage-edit", kwargs={"pk": storage.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    storage.refresh_from_db()
    assert storage.row_labels_enabled is True

    data["row_labels_enabled"] = ""
    with django_assert_num_queries(15):
        r = client.post(
            reverse("storage-edit", kwargs={"pk": storage.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    storage.refresh_from_db()
    assert storage.row_labels_enabled is False


@pytest.mark.django_db
def test_storage_update_post_column_labels_enabled(
    client, user, django_assert_num_queries
):
    client.force_login(user)
    storage = Storage.objects.first()
    data = {
        "name": storage.name,
        "location": "Basement",
        "rows": 1,
        "columns": 10,
        "column_labels_enabled": "on",
    }
    with django_assert_num_queries(16):
        r = client.post(
            reverse("storage-edit", kwargs={"pk": storage.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    storage.refresh_from_db()
    assert storage.column_labels_enabled is True

    data["column_labels_enabled"] = ""
    with django_assert_num_queries(15):
        r = client.post(
            reverse("storage-edit", kwargs={"pk": storage.pk}), data=data, follow=True
        )
    assert r.status_code == HTTPStatus.OK
    storage.refresh_from_db()
    assert storage.column_labels_enabled is False


@pytest.mark.django_db
def test_storage_cant_delete_only(client, user, django_assert_num_queries):
    client.force_login(user)
    assert Storage.objects.count() == 1
    storage = Storage.objects.first()
    with django_assert_num_queries(5):
        r = client.post(
            reverse("storage-delete", kwargs={"pk": storage.pk}), follow=True
        )
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors


@pytest.mark.django_db
def test_storage_cant_delete_other_users(
    client, user, user_factory, storage_factory, django_assert_num_queries
):
    other_user = user_factory()
    storage_other_user = storage_factory(user=other_user)
    client.force_login(user)
    assert Storage.objects.count() == 3
    with django_assert_num_queries(3):
        r = client.post(
            reverse("storage-delete", kwargs={"pk": storage_other_user.pk}),
            follow=True,
        )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert Storage.objects.count() == 3


@pytest.mark.django_db
def test_storage_can_delete_multiple(
    client, user, storage_factory, django_assert_num_queries
):
    client.force_login(user)
    storage_factory(user=user)
    assert Storage.objects.count() == 2
    storage = Storage.objects.first()
    with django_assert_num_queries(13):
        r = client.post(
            reverse("storage-delete", kwargs={"pk": storage.pk}), follow=True
        )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("storage-list"))
    assert Storage.objects.count() == 1


# ---------------------------------------------------------------------------
# StorageListView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_storage_list_view(client, user, django_assert_num_queries):
    client.force_login(user)
    with django_assert_num_queries(6):
        r = client.get(reverse("storage-list"))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="storage_list.html")


@pytest.mark.django_db
def test_storage_list_unauthenticated(client, user, django_assert_num_queries):
    with django_assert_num_queries(1):
        r = client.get(reverse("storage-list"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login") + "?next=" + reverse("storage-list"),
    )


# ---------------------------------------------------------------------------
# StorageDetailView
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_storage_detail_view(
    client, user, wine_factory, storage_item_factory, django_assert_num_queries
):
    storage = Storage.objects.filter(user=user).first()
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, vintage=wine.latest_vintage)
    client.force_login(user)
    with django_assert_num_queries(9):
        r = client.get(reverse("storage-detail", kwargs={"pk": storage.pk}))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="storage_detail.html")


@pytest.mark.django_db
def test_storage_detail_other_user_returns_404(
    client, user, user_factory, storage_factory, django_assert_num_queries
):
    other_user = user_factory()
    other_storage = Storage.objects.filter(user=other_user).first()
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.get(reverse("storage-detail", kwargs={"pk": other_storage.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND
