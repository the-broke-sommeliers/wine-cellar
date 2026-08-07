from http import HTTPStatus
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import httpx
import litellm.exceptions
import pytest
from django.core.cache import caches
from django.test import override_settings
from django.urls import resolve, reverse

from tests.helpers import random_png

wine_prefill_cache = caches["wine_prefill"]


def _make_litellm_exc(exc_cls, status=503):
    req = httpx.Request("POST", "https://api.example.com/")
    resp = httpx.Response(status, request=req)
    return exc_cls("test error", llm_provider="test", model="test", response=resp)


def _poll(client, poll_url):
    """Follow up on a `wine-ai-upload` response by polling its `poll_url`.

    `CELERY_TASK_ALWAYS_EAGER=True` (test.py) means the task has already run
    to completion by the time the initial POST returns, so a single poll
    always reflects the final ("done"/"error") state.
    """
    r = client.get(poll_url)
    return r.json()


def _prefill_data(poll_url):
    token = resolve(urlparse(poll_url).path).kwargs["token"]
    return wine_prefill_cache.get(f"wine_prefill_{token}")


def _mock_response(content):
    resp = MagicMock()
    resp.choices[0].message.content = content
    return resp


@pytest.mark.django_db
def test_wine_choose_action_ai_disabled(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-add-choose"))
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["ai_enabled"] is False


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
def test_wine_choose_action_ai_enabled(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-add-choose"))
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["ai_enabled"] is True


@pytest.mark.django_db
def test_wine_choose_action_with_barcode(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-add-choose") + "?barcode=9780201633610")
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["barcode"] == "9780201633610"
    token = r.context_data["prefill_token"]
    data = wine_prefill_cache.get(f"wine_prefill_{token}")
    assert data["initial"]["barcode"] == "9780201633610"


@pytest.mark.django_db
def test_ai_upload_no_images_rejected(client, user):
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={})
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json()["errors"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_success_returns_poll_url_and_then_create(
    mock_completion, client, user
):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll_url = r.json()["poll_url"]
    assert resolve(urlparse(poll_url).path).url_name == "wine-ai-upload-poll"

    poll = _poll(client, poll_url)
    assert poll["status"] == "done"
    assert reverse("wine-add") in poll["redirect"]
    assert "prefill_token" in poll["redirect"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_prefill_not_visible_to_other_user(
    mock_completion, client, user, user_factory
):
    """A guessed/observed `prefill_token` from someone else's AI upload must
    not prefill the create form for a different logged-in user."""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Secret Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    token = resolve(urlparse(r.json()["poll_url"]).path).kwargs["token"]

    other_user = user_factory()
    client.force_login(other_user)
    r = client.get(reverse("wine-add") + f"?prefill_token={token}")
    assert r.status_code == HTTPStatus.OK
    initial = {k: v for k, v in r.context_data["form"].initial.items() if v is not None}
    assert "name" not in initial
    assert r.context_data["ai_images_pending"] is False

    # the original owner's entry must be untouched
    data = wine_prefill_cache.get(f"wine_prefill_{token}")
    assert data["user_id"] == user.pk
    assert data["initial"]["name"] == "Secret Wine"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_json_inside_markdown_block(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '```json\n{"name": "Test Wine"}\n```'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "done"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_json_shows_error(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "not valid json at all"
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "error"
    assert poll["message"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_authentication_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.AuthenticationError, status=401
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "error"
    assert poll["message"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_rate_limit_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.RateLimitError, status=429
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "error"
    assert poll["message"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_service_unavailable_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.ServiceUnavailableError, status=503
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "error"
    assert poll["message"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_timeout_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.Timeout(
        "timeout", model="test", llm_provider="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "error"
    assert poll["message"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_connection_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.APIConnectionError(
        "connection error", llm_provider="test", model="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "error"
    assert poll["message"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_back_image_only(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"back": random_png("back.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "done"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_success_with_barcode_param(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    url = reverse("wine-ai-upload") + "?barcode=12345"
    r = client.post(url, data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert "barcode" not in r.json()["poll_url"]
    data = _prefill_data(r.json()["poll_url"])
    assert data["initial"]["barcode"] == "12345"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_use_as_wine_images_checked_stashes_images(
    mock_completion, client, user
):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(
        reverse("wine-ai-upload"),
        data={"front": random_png("front.png"), "use_as_wine_images": "on"},
    )
    assert r.status_code == HTTPStatus.OK
    data = _prefill_data(r.json()["poll_url"])
    assert data["images"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_use_as_wine_images_unchecked_no_images_stashed(
    mock_completion, client, user
):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    data = _prefill_data(r.json()["poll_url"])
    assert data["images"] == {}


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_api_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.APIError(
        status_code=500, message="api error", llm_provider="test", model="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "error"
    assert poll["message"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_unicode_minus_location_succeeds_without_reprompt(
    mock_completion, client, user
):
    mock_completion.return_value = _mock_response(
        '{"name": "Test Wine", "location": "48.1374,−0.6603"}'
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 1
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert initial["location"]["geometry"]["coordinates"] == [-0.6603, 48.1374]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_location_reprompt_succeeds(mock_completion, client, user):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "location": "999,999"}'),
        _mock_response('{"location": "48.1374,-0.6603"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert initial["location"]["geometry"]["coordinates"] == [-0.6603, 48.1374]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_location_reprompt_still_invalid_drops_location(
    mock_completion, client, user
):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "location": "999,999"}'),
        _mock_response('{"location": "888,888"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert "location" not in initial


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_location_reprompt_bad_json_drops_location(
    mock_completion, client, user
):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "location": "999,999"}'),
        _mock_response("not valid json"),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert "location" not in initial


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_location_reprompt_litellm_error_drops_location(
    mock_completion, client, user
):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "location": "999,999"}'),
        _make_litellm_exc(litellm.exceptions.ServiceUnavailableError),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert "location" not in initial


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_missing_location_no_reprompt(mock_completion, client, user):
    mock_completion.return_value = _mock_response('{"name": "Test Wine"}')
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 1


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_country_reprompt_succeeds(mock_completion, client, user):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "country": "Germany"}'),
        _mock_response('{"country": "DE"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert initial["country"] == "DE"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_country_reprompt_still_invalid_drops_country(
    mock_completion, client, user
):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "country": "Germany"}'),
        _mock_response('{"country": "Deutschland"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert "country" not in initial


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_type_reprompt_succeeds(mock_completion, client, user):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "type": "vino rosso"}'),
        _mock_response('{"type": "red"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert initial["wine_type"] == "RE"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_type_reprompt_still_invalid_drops_type(
    mock_completion, client, user
):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "type": "vino rosso"}'),
        _mock_response('{"type": "vino ancora rosso"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert "wine_type" not in initial


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_sweetness_reprompt_succeeds(mock_completion, client, user):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "sweetness": "sec"}'),
        _mock_response('{"sweetness": "dry"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert initial["category"] == "DR"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.completion")
def test_ai_upload_invalid_sweetness_reprompt_still_invalid_drops_sweetness(
    mock_completion, client, user
):
    mock_completion.side_effect = [
        _mock_response('{"name": "Test Wine", "sweetness": "sec"}'),
        _mock_response('{"sweetness": "encore sec"}'),
    ]
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 2
    initial = _prefill_data(r.json()["poll_url"])["initial"]
    assert "category" not in initial


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.tasks.process_ai_wine_upload.delay")
def test_ai_upload_dispatch_failure_shows_form_error(mock_delay, client, user):
    """If queuing the Celery task itself fails (e.g. broker unreachable),
    the view must respond with a JSON error instead of a `poll_url` that
    would poll forever."""
    mock_delay.side_effect = ConnectionError("broker unreachable")
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert r.json()["errors"]["__all__"]
