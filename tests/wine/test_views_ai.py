from http import HTTPStatus
from unittest.mock import MagicMock, patch

import httpx
import litellm.exceptions
import pytest
from django.test import override_settings
from django.urls import reverse

from tests.helpers import random_png


def _make_litellm_exc(exc_cls, status=503):
    req = httpx.Request("POST", "https://api.example.com/")
    resp = httpx.Response(status, request=req)
    return exc_cls("test error", llm_provider="test", model="test", response=resp)


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


@pytest.mark.django_db
def test_ai_upload_no_images_rejected(client, user):
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_success_redirects_to_create(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine", "country": "DE"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert reverse("wine-add") in r["Location"]
    assert "ai_initial" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_json_inside_markdown_block(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '```json\n{"name": "Test Wine"}\n```'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert "ai_initial" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_invalid_json_shows_error(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "not valid json at all"
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_authentication_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.AuthenticationError, status=401
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_rate_limit_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.RateLimitError, status=429
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_service_unavailable_error(mock_completion, client, user):
    mock_completion.side_effect = _make_litellm_exc(
        litellm.exceptions.ServiceUnavailableError, status=503
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_timeout_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.Timeout(
        "timeout", model="test", llm_provider="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_connection_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.APIConnectionError(
        "connection error", llm_provider="test", model="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_back_image_only(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"back": random_png("back.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert "ai_initial" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_success_with_barcode_param(mock_completion, client, user):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = '{"name": "Test Wine"}'
    mock_completion.return_value = mock_resp
    client.force_login(user)
    url = reverse("wine-ai-upload") + "?barcode=12345"
    r = client.post(url, data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.FOUND
    assert "barcode=12345" in r["Location"]


@pytest.mark.django_db
@override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")
@patch("wine_cellar.apps.wine.views.completion")
def test_ai_upload_api_error(mock_completion, client, user):
    mock_completion.side_effect = litellm.exceptions.APIError(
        status_code=500, message="api error", llm_provider="test", model="test"
    )
    client.force_login(user)
    r = client.post(reverse("wine-ai-upload"), data={"front": random_png("front.png")})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].non_field_errors()
