from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from pytest_django.asserts import assertRedirects

from wine_cellar.apps.user.context_processors import whats_new
from wine_cellar.apps.user.whats_new import (
    WhatsNewRelease,
    get_latest_whats_new_version,
    get_unseen_releases,
)


@pytest.mark.django_db
def test_whats_new_shown_for_user_with_no_settings_row(client, user):
    client.force_login(user)
    r = client.get(reverse("homepage"))
    assert r.status_code == HTTPStatus.OK
    assert "What's New" in r.content.decode()


@pytest.mark.django_db
def test_whats_new_hidden_when_all_seen(client, user, user_settings_factory):
    user_settings_factory(
        user=user, last_seen_whats_new_version=get_latest_whats_new_version()
    )
    client.force_login(user)
    r = client.get(reverse("homepage"))
    assert r.status_code == HTTPStatus.OK
    assert "What's New" not in r.content.decode()


@pytest.mark.django_db
def test_whats_new_hidden_for_unrecognized_last_seen_version(
    client, user, user_settings_factory
):
    user_settings_factory(user=user, last_seen_whats_new_version="9.9.9-unknown")
    client.force_login(user)
    r = client.get(reverse("homepage"))
    assert r.status_code == HTTPStatus.OK
    assert "What's New" not in r.content.decode()


@pytest.mark.django_db
def test_whats_new_hidden_for_anonymous_user(client):
    r = client.get(reverse("account_login"))
    assert r.status_code == HTTPStatus.OK
    assert "What's New" not in r.content.decode()


@pytest.mark.django_db
@override_settings(ENABLE_WHATS_NEW=False)
def test_whats_new_hidden_when_disabled(client, user):
    client.force_login(user)
    r = client.get(reverse("homepage"))
    assert r.status_code == HTTPStatus.OK
    assert "What's New" not in r.content.decode()


@pytest.mark.django_db
def test_whats_new_dismiss_updates_last_seen_and_redirects(client, user):
    client.force_login(user)
    r = client.post(
        reverse("whats-new-dismiss"), {"next": reverse("homepage")}, follow=True
    )
    assertRedirects(response=r, expected_url=reverse("homepage"))
    user.user_settings.refresh_from_db()
    assert (
        user.user_settings.last_seen_whats_new_version == get_latest_whats_new_version()
    )


@pytest.mark.django_db
def test_whats_new_dismiss_rejects_unsafe_next(client, user):
    client.force_login(user)
    r = client.post(
        reverse("whats-new-dismiss"),
        {"next": "https://evil.example/"},
        follow=True,
    )
    assertRedirects(response=r, expected_url=reverse("homepage"))


@pytest.mark.django_db
def test_whats_new_cache_prevents_repeat_query(rf, user):
    # Use a fresh User instance per simulated request, like the real
    # AuthenticationMiddleware would on each HTTP request - a single shared
    # instance would mask the DB query behind Django's own per-instance
    # caching of the user_settings reverse accessor.
    User = get_user_model()

    request = rf.get("/")
    request.user = User.objects.get(pk=user.pk)
    with CaptureQueriesContext(connection) as ctx:
        whats_new(request)
    first_hits = sum(1 for q in ctx.captured_queries if "user_usersettings" in q["sql"])

    request = rf.get("/")
    request.user = User.objects.get(pk=user.pk)
    with CaptureQueriesContext(connection) as ctx:
        whats_new(request)
    second_hits = sum(
        1 for q in ctx.captured_queries if "user_usersettings" in q["sql"]
    )

    assert first_hits == 1
    assert second_hits == 0


@pytest.mark.django_db
def test_whats_new_dismiss_updates_cache_immediately(client, rf, user):
    User = get_user_model()
    client.force_login(user)

    request = rf.get("/")
    request.user = User.objects.get(pk=user.pk)
    whats_new(request)  # populate the cache with the pre-dismiss value

    client.post(reverse("whats-new-dismiss"), {"next": reverse("homepage")})

    request = rf.get("/")
    request.user = User.objects.get(pk=user.pk)
    with CaptureQueriesContext(connection) as ctx:
        context = whats_new(request)
    hits = sum(1 for q in ctx.captured_queries if "user_usersettings" in q["sql"])

    assert context["whats_new_releases"] == []
    assert hits == 0


def test_get_unseen_releases(monkeypatch):
    releases = [
        WhatsNewRelease(version="0.3.0", items=["c"]),
        WhatsNewRelease(version="0.2.0", items=["b"]),
        WhatsNewRelease(version="0.1.0", items=["a"]),
    ]
    monkeypatch.setattr("wine_cellar.apps.user.whats_new.WHATS_NEW_RELEASES", releases)

    assert get_unseen_releases("") == releases
    assert get_unseen_releases("0.2.0") == [releases[0]]
    assert get_unseen_releases("0.3.0") == []
    assert get_unseen_releases("9.9.9-unknown") == []
