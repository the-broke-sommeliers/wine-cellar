from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateUsed,
)

from wine_cellar.apps.storage.models import Storage


@pytest.mark.django_db
def test_storage_create_page_unauthenticated(client, user):
    r = client.get(reverse("storage-add"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("login") + "?next=" + reverse("storage-add")
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="registration/login.html")


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
        response=r, expected_url=reverse("login") + "?next=" + reverse("storage-add")
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="registration/login.html")
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
    r = client.get(reverse("storage-add"))
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
