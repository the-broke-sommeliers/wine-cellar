import json
from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed


@pytest.mark.django_db
def test_wine_map_view(client, user, wine_factory, django_assert_num_queries):
    wine_factory(user=user)
    client.force_login(user)
    with django_assert_num_queries(6):
        r = client.get(reverse("wine-map"))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="wine_map.html")


@pytest.mark.django_db
def test_wine_map_view_query_count_does_not_scale_with_wine_count(
    client, user, wine_factory, django_assert_num_queries
):
    """Regression test for an N+1: each wine's latest_vintage/image used to
    be looked up with its own query per wine instead of being prefetched."""
    wine_factory(user=user)
    client.force_login(user)
    with django_assert_num_queries(6):
        client.get(reverse("wine-map"))

    wine_factory(user=user)
    wine_factory(user=user)
    with django_assert_num_queries(5):
        r = client.get(reverse("wine-map"))
    assert r.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_health_check(client, django_assert_num_queries):
    with django_assert_num_queries(1):
        r = client.get(reverse("health_check"))
    assert r.status_code == HTTPStatus.OK
    data = json.loads(r.content)
    assert data["status"] == "ok"
