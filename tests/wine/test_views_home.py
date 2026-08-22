from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateNotUsed,
    assertTemplateUsed,
)


@pytest.mark.django_db
def test_homepage_unauthenticated(client, django_assert_num_queries):
    with django_assert_num_queries(1):
        r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("account_login") + "?next=/")
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_homepage(client, user, django_assert_num_queries):
    client.force_login(user)
    with django_assert_num_queries(10):
        r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="homepage.html")
    assertTemplateNotUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_admin_link_hidden_from_regular_user(client, user, django_assert_num_queries):
    client.force_login(user)
    with django_assert_num_queries(10):
        r = client.get(reverse("homepage"))
    assert r.status_code == HTTPStatus.OK
    assert reverse("admin:index") not in r.content.decode()


@pytest.mark.django_db
def test_admin_link_visible_to_staff_user(client, user, django_assert_num_queries):
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    client.force_login(user)
    with django_assert_num_queries(10):
        r = client.get(reverse("homepage"))
    assert r.status_code == HTTPStatus.OK
    assert reverse("admin:index") in r.content.decode()


@pytest.mark.django_db
def test_homepage_stats(
    client,
    user,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage = vintage_factory(wine=wine, year=2020)
    storage = user.storage_set.first()
    wine_2 = wine_factory(user=user, country="DE", _create_default_vintage=False)
    vintage_2 = vintage_factory(wine=wine_2, year=2023, price=15.00)
    wine_3 = wine_factory(user=user, country="ES", _create_default_vintage=False)
    vintage_factory(wine=wine_3, year=2024)
    storage_item_factory(vintage=vintage, storage=storage, price=10.50)
    storage_item_factory(vintage=vintage, storage=storage, price=5.25)
    storage_item_factory(vintage=vintage, storage=storage, price=8.99, deleted=True)
    storage_item_factory(vintage=vintage_2, storage=storage, price=4.99, deleted=True)
    storage_item_factory(vintage=vintage_2, storage=storage, price=12.00)
    storage_item_factory(vintage=vintage_2, storage=storage)
    client.force_login(user)
    with django_assert_num_queries(10):
        r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="homepage.html")
    assertTemplateNotUsed(response=r, template_name="registration/login.html")
    assert r.context_data["oldest"] == 2020
    assert r.context_data["youngest"] == 2024
    # we only count wines in stock, not bottles
    assert r.context_data["wines_in_stock"] == 2
    assert r.context_data["wines"] == 3
    assert r.context_data["countries"] == 2
    assert r.context_data["total_value"] == "43€"
