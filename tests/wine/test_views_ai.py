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
from wine_cellar.apps.wine.models import Size

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
def test_wine_upload_ai_page_ai_disabled_by_default(client, user):
    """`WineUploadAIView.get_context_data` computes its own `ai_enabled`
    flag independently of `WineChooseActionView`'s (different `hasattr`-
    based implementation) - assert it directly rather than relying on the
    other view's test to catch a regression here."""
    client.force_login(user)
    r = client.get(reverse("wine-ai-upload"))
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["ai_enabled"] is False


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
def test_wine_upload_ai_page_ai_enabled_with_settings(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-ai-upload"))
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
@patch("litellm.completion")
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
def test_ai_upload_poll_unknown_token_returns_expired_error(client, user):
    """Every other poll test only polls *after* `CELERY_TASK_ALWAYS_EAGER`
    has already driven the task to a final state - nobody polls a token
    that was never created (or already expired from the cache)."""
    client.force_login(user)
    r = client.get(reverse("wine-ai-upload-poll", kwargs={"token": "bogus-token"}))
    assert r.status_code == HTTPStatus.OK
    body = r.json()
    assert body["status"] == "error"
    assert body["message"]


@pytest.mark.django_db
def test_ai_upload_poll_other_users_token_returns_expired_error(
    client, user, user_factory
):
    token = "shared-token"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": {"name": "Secret Wine"},
            "images": {},
            "user_id": user.pk,
        },
        timeout=60,
    )
    other_user = user_factory()
    client.force_login(other_user)
    r = client.get(reverse("wine-ai-upload-poll", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.OK
    assert r.json()["status"] == "error"


@pytest.mark.django_db
def test_ai_upload_poll_pending_status(client, user):
    """No mocked litellm call needed - write a "pending" entry directly
    into the cache to observe the poll view's in-progress branch, which
    `CELERY_TASK_ALWAYS_EAGER` otherwise never leaves time to observe."""
    token = "pending-token"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {"status": "pending", "stage": "reprompt_country", "user_id": user.pk},
        timeout=60,
    )
    client.force_login(user)
    r = client.get(reverse("wine-ai-upload-poll", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.OK
    assert r.json() == {"status": "pending", "stage": "reprompt_country"}


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
def test_ai_upload_missing_location_no_reprompt(mock_completion, client, user):
    mock_completion.return_value = _mock_response('{"name": "Test Wine"}')
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert mock_completion.call_count == 1


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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
@patch("litellm.completion")
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


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_ai_upload_poll_done_with_match_redirects_to_existing_match_view(
    mock_completion, client, user, wine_factory
):
    """When the AI-extracted name/type/size/country match a wine the user
    already has, the poll should route to the disambiguation page instead
    of straight to the create form."""
    size = Size.objects.get(name=0.75)
    wine_factory(user=user, name="Merlot", wine_type="RE", size=size, country="DE")
    mock_completion.return_value = _mock_response(
        '{"name": "Merlot", "country": "DE", "type": "red", "size": "0.75"}'
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "done"
    assert resolve(urlparse(poll["redirect"]).path).url_name == "wine-ai-existing-match"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_ai_upload_poll_done_with_case_differing_name_redirects_to_existing_match_view(
    mock_completion, client, user, wine_factory
):
    """A repeat AI scan of the same label can come back with different name
    casing - that must still be treated as a match, not a silent duplicate."""
    size = Size.objects.get(name=0.75)
    wine_factory(user=user, name="Merlot", wine_type="RE", size=size, country="DE")
    mock_completion.return_value = _mock_response(
        '{"name": "MERLOT", "country": "DE", "type": "red", "size": "0.75"}'
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "done"
    assert resolve(urlparse(poll["redirect"]).path).url_name == "wine-ai-existing-match"


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("litellm.completion")
def test_ai_upload_poll_done_partial_initial_skips_match_check(
    mock_completion, client, user, wine_factory
):
    """If the AI couldn't resolve a size (never present in `initial`), there
    isn't enough information to match against the DB's uniqueness rule -
    behavior must stay exactly as before this feature, even if a same-named
    wine exists."""
    wine_factory(user=user, name="Merlot", wine_type="RE", country="DE")
    mock_completion.return_value = _mock_response(
        '{"name": "Merlot", "country": "DE", "type": "red"}'
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    poll = _poll(client, r.json()["poll_url"])
    assert poll["status"] == "done"
    assert reverse("wine-add") in poll["redirect"]


@pytest.mark.django_db
def test_ai_existing_match_view_renders_matched_wine(client, user, wine_factory):
    size = Size.objects.get(name=0.75)
    wine = wine_factory(
        user=user, name="Merlot", wine_type="RE", size=size, country="DE"
    )
    token = "match-token"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": {
                "name": "Merlot",
                "wine_type": "RE",
                "size": size.pk,
                "country": "DE",
            },
            "images": {},
            "user_id": user.pk,
        },
        timeout=60,
    )
    client.force_login(user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["wine"] == wine
    assert r.context["prefill_token"] == token
    assert "existing_vintage_year" not in r.context
    assert "name_case_differs" not in r.context


@pytest.mark.django_db
def test_ai_existing_match_view_flags_case_differing_name(client, user, wine_factory):
    size = Size.objects.get(name=0.75)
    wine = wine_factory(
        user=user, name="Chapel Down Bacchus", wine_type="WH", size=size, country="GB"
    )
    token = "case-match-token"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": {
                "name": "CHAPEL DOWN BACCHUS",
                "wine_type": "WH",
                "size": size.pk,
                "country": "GB",
            },
            "images": {},
            "user_id": user.pk,
        },
        timeout=60,
    )
    client.force_login(user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["wine"] == wine
    assert r.context["name_case_differs"] is True
    assert "looks very similar" in r.content.decode()


@pytest.mark.django_db
def test_ai_existing_match_view_flags_colliding_vintage_year(
    client, user, wine_factory, vintage_factory
):
    """When the AI also extracted a year that collides with an existing
    vintage of the matched wine, the disambiguation page should surface
    that up front, not just let the user hit the error after submitting
    the add-vintage form."""
    size = Size.objects.get(name=0.75)
    wine = wine_factory(
        user=user,
        name="Merlot",
        wine_type="RE",
        size=size,
        country="DE",
        _create_default_vintage=False,
    )
    vintage_factory(wine=wine, year=2020)
    token = "match-token-with-year"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": {
                "name": "Merlot",
                "wine_type": "RE",
                "size": size.pk,
                "country": "DE",
                "year": 2020,
            },
            "images": {},
            "user_id": user.pk,
        },
        timeout=60,
    )
    client.force_login(user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["existing_vintage_year"] == 2020
    assert "2020" in r.content.decode()


@pytest.mark.django_db
def test_ai_existing_match_view_no_vintage_warning_for_new_year(
    client, user, wine_factory, vintage_factory
):
    size = Size.objects.get(name=0.75)
    wine = wine_factory(
        user=user,
        name="Merlot",
        wine_type="RE",
        size=size,
        country="DE",
        _create_default_vintage=False,
    )
    vintage_factory(wine=wine, year=2019)
    token = "match-token-different-year"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": {
                "name": "Merlot",
                "wine_type": "RE",
                "size": size.pk,
                "country": "DE",
                "year": 2020,
            },
            "images": {},
            "user_id": user.pk,
        },
        timeout=60,
    )
    client.force_login(user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.OK
    assert "existing_vintage_year" not in r.context


@pytest.mark.django_db
def test_ai_existing_match_view_no_longer_matching_redirects_to_wine_add(client, user):
    """The token's initial payload looks like a match, but no such wine
    actually exists (e.g. it was deleted or edited after the poll computed
    the redirect) - fall back gracefully to the normal create form."""
    token = "stale-token"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": {
                "name": "Merlot",
                "wine_type": "RE",
                "size": 1,
                "country": "DE",
            },
            "images": {},
            "user_id": user.pk,
        },
        timeout=60,
    )
    client.force_login(user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == f"{reverse('wine-add')}?prefill_token={token}"


@pytest.mark.django_db
def test_ai_existing_match_view_expired_token_redirects_to_wine_add(client, user):
    client.force_login(user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": "bogus"}))
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == f"{reverse('wine-add')}?prefill_token=bogus"


@pytest.mark.django_db
def test_ai_existing_match_view_other_users_token_redirects_to_wine_add(
    client, user, user_factory, wine_factory
):
    size = Size.objects.get(name=0.75)
    wine_factory(user=user, name="Merlot", wine_type="RE", size=size, country="DE")
    token = "shared-token"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": {
                "name": "Merlot",
                "wine_type": "RE",
                "size": size.pk,
                "country": "DE",
            },
            "images": {},
            "user_id": user.pk,
        },
        timeout=60,
    )
    other_user = user_factory()
    client.force_login(other_user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == f"{reverse('wine-add')}?prefill_token={token}"


@pytest.mark.django_db
def test_ai_existing_match_view_pending_status_redirects_to_wine_add(client, user):
    token = "pending-token"
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {"status": "pending", "user_id": user.pk},
        timeout=60,
    )
    client.force_login(user)
    r = client.get(reverse("wine-ai-existing-match", kwargs={"token": token}))
    assert r.status_code == HTTPStatus.FOUND
    assert r.url == f"{reverse('wine-add')}?prefill_token={token}"
