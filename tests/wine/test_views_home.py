from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateNotUsed,
    assertTemplateUsed,
)


@pytest.mark.django_db
def test_homepage_unauthenticated(client):
    r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("account_login") + "?next=/")
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_homepage(client, user):
    client.force_login(user)
    r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="homepage.html")
    assertTemplateNotUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_homepage_stats(client, user, wine_factory, storage_item_factory):
    wine = wine_factory(user=user, vintage=2020)
    storage = user.storage_set.first()
    wine_2 = wine_factory(user=user, country="DE", vintage=2023, price=15.00)
    wine_factory(user=user, country="ES", vintage=2024)
    storage_item_factory(wine=wine, storage=storage, price=10.50)
    storage_item_factory(wine=wine, storage=storage, price=5.25)
    storage_item_factory(wine=wine, storage=storage, price=8.99, deleted=True)
    storage_item_factory(wine=wine_2, storage=storage, price=4.99, deleted=True)
    storage_item_factory(wine=wine_2, storage=storage, price=12.00)
    storage_item_factory(wine=wine_2, storage=storage)
    client.force_login(user)
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
