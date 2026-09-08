import json
from http import HTTPStatus

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_check(client, django_assert_num_queries):
    with django_assert_num_queries(1):
        r = client.get(reverse("health_check"))
    assert r.status_code == HTTPStatus.OK
    data = json.loads(r.content)
    assert data["status"] == "ok"
