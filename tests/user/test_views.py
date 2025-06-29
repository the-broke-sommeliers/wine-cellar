from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed


@pytest.mark.django_db
def test_user_settings_page(client, user):
    client.force_login(user)
    r = client.get(reverse("user-settings"))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="settings.html")

    data = {
        "language": "de-DE",
        "currency": "EUR",
        "notifications": True,
    }
    r = client.post(reverse("user-settings"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("user-settings"))
    user_settings = user.user_settings
    assert user_settings.language == "de-DE"
    assert user_settings.currency == "EUR"
    assert user_settings.notifications

    data = {
        "language": "en-gb",
        "currency": "EUR",
        "notifications": False,
    }
    r = client.post(reverse("user-settings"), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    user_settings.refresh_from_db()
    assert user_settings.language == "en-gb"
    assert user_settings.currency == "EUR"
    assert not user_settings.notifications
