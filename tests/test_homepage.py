from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import (
    assertRedirects,
    assertTemplateNotUsed,
    assertTemplateUsed,
)


def test_homepage_unauthenticated(client):
    r = client.get(reverse("homepage"), follow=True)
    assertRedirects(response=r, expected_url=reverse("login"))
    assertTemplateUsed(response=r, template_name="registration/login.html")


@pytest.mark.django_db
def test_homepage_authenticated(client, user):
    client.force_login(user)
    r = client.get(reverse("homepage"), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateNotUsed(response=r, template_name="registration/login.html")
