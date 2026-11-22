import re
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import litellm.exceptions
import pytest
from django.test import override_settings
from django.urls import reverse

from wine_cellar.apps.wine.models import Category
from wine_cellar.apps.wine.tasks import generate_ai_tasting_notes
from wine_cellar.apps.wine.utils import ai_tasting_notes_cache_key, wine_prefill_cache

ai_settings = override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")


def _mock_response(content):
    resp = MagicMock()
    resp.choices[0].message.content = content
    return resp


def _urls(vintage):
    kwargs = {"wine_pk": vintage.wine_id, "pk": vintage.pk}
    return (
        reverse("vintage-ai-tasting-notes", kwargs=kwargs),
        reverse("vintage-ai-tasting-notes-poll", kwargs=kwargs),
        reverse("vintage-ai-tasting-notes-delete", kwargs=kwargs),
    )


@pytest.fixture
def vintage(user, wine_factory, vintage_factory, grape_factory, region_factory):
    wine = wine_factory(
        user=user,
        name="Barolo Riserva",
        country="IT",
        category=Category.DRY,
        region=region_factory(name="Piedmont", user=user),
        grapes=[grape_factory(name="Nebbiolo", user=user)],
        _create_default_vintage=False,
    )
    return vintage_factory(wine=wine, year=2016, abv=14.5)


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_generate_saves_notes_and_poll_returns_them(
    mock_completion, client, user, vintage, user_settings_factory
):
    user_settings_factory(user=user, language="de-DE")
    mock_completion.return_value = _mock_response("  Ruby red, rose and tar.  ")
    client.force_login(user)
    generate_url, poll_url, _ = _urls(vintage)

    r = client.post(generate_url)
    assert r.status_code == HTTPStatus.OK
    assert r.json()["poll_url"] == poll_url

    vintage.refresh_from_db()
    assert vintage.ai_tasting_notes == "Ruby red, rose and tar."
    assert client.get(poll_url).json() == {
        "status": "done",
        "text": "Ruby red, rose and tar.",
    }

    prompt = mock_completion.call_args.kwargs["messages"][0]["content"]
    for expected in (
        "Barolo Riserva",
        "Nebbiolo",
        "Piedmont",
        "Italy",
        "2016",
        "14.5%",
        "Write in German",
    ):
        assert expected in prompt


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_generate_maps_litellm_errors(mock_completion, client, user, vintage):
    mock_completion.side_effect = litellm.exceptions.Timeout(
        "timeout", model="test", llm_provider="test"
    )
    client.force_login(user)
    generate_url, poll_url, _ = _urls(vintage)

    client.post(generate_url)

    data = client.get(poll_url).json()
    assert data["status"] == "error"
    assert "timed out" in data["message"]
    vintage.refresh_from_db()
    assert vintage.ai_tasting_notes == ""


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_generate_empty_response_is_error(mock_completion, client, user, vintage):
    mock_completion.return_value = _mock_response(None)
    client.force_login(user)
    generate_url, poll_url, _ = _urls(vintage)

    client.post(generate_url)

    assert client.get(poll_url).json()["status"] == "error"


@pytest.mark.django_db
@ai_settings
def test_poll_without_request_returns_expired(client, user, vintage):
    client.force_login(user)
    _, poll_url, _ = _urls(vintage)
    data = client.get(poll_url).json()
    assert data["status"] == "error"


@pytest.mark.django_db
@ai_settings
@patch("wine_cellar.apps.wine.views.generate_ai_tasting_notes.delay")
def test_generate_queue_failure_returns_400(mock_delay, client, user, vintage):
    mock_delay.side_effect = RuntimeError("broker down")
    client.force_login(user)
    generate_url, _, _ = _urls(vintage)

    r = client.post(generate_url)

    assert r.status_code == HTTPStatus.BAD_REQUEST
    assert wine_prefill_cache.get(ai_tasting_notes_cache_key(vintage.pk)) is None


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_other_users_vintage_returns_404(
    mock_completion, client, user_factory, vintage
):
    vintage.ai_tasting_notes = "keep me"
    vintage.save()
    client.force_login(user_factory())
    generate_url, poll_url, delete_url = _urls(vintage)

    assert client.post(generate_url).status_code == HTTPStatus.NOT_FOUND
    assert client.get(poll_url).status_code == HTTPStatus.NOT_FOUND
    assert client.post(delete_url).status_code == HTTPStatus.NOT_FOUND
    mock_completion.assert_not_called()
    vintage.refresh_from_db()
    assert vintage.ai_tasting_notes == "keep me"


@pytest.mark.django_db
def test_generate_and_poll_404_when_ai_disabled(client, user, vintage):
    client.force_login(user)
    generate_url, poll_url, _ = _urls(vintage)
    assert client.post(generate_url).status_code == HTTPStatus.NOT_FOUND
    assert client.get(poll_url).status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_delete_clears_notes_even_when_ai_disabled(client, user, vintage):
    vintage.ai_tasting_notes = "old text"
    vintage.save()
    client.force_login(user)
    _, _, delete_url = _urls(vintage)

    r = client.post(delete_url)

    assert r.status_code == HTTPStatus.FOUND
    assert r.url == reverse("wine-detail", kwargs={"pk": vintage.wine_id})
    vintage.refresh_from_db()
    assert vintage.ai_tasting_notes == ""


@pytest.mark.django_db
def test_detail_page_ai_box_buttons(client, user, vintage, food_pairing_factory):
    # Hides the wine-level food pairings Generate button.
    vintage.wine.food_pairings.add(food_pairing_factory(name="Lamb", user=user))
    client.force_login(user)
    url = reverse("wine-detail", kwargs={"pk": vintage.wine_id})
    generate_url, _, delete_url = _urls(vintage)
    edit_url = reverse(
        "vintage-ai-tasting-notes-edit",
        kwargs={"wine_pk": vintage.wine_id, "pk": vintage.pk},
    )
    remove_hidden = re.compile(rf'action="{delete_url}"\s+class="hidden"')
    ai_disabled_title = "AI is not configured on this server."

    # No notes, AI disabled: disabled Generate, Edit, no Remove.
    content = client.get(url).content.decode()
    assert "data-ai-generate" not in content
    assert ai_disabled_title in content
    assert edit_url in content
    assert remove_hidden.search(content)

    # No notes, AI enabled: working Generate, Edit, no Remove.
    with ai_settings:
        content = client.get(url).content.decode()
    assert f'data-ai-generate="{generate_url}"' in content
    assert ai_disabled_title not in content
    assert edit_url in content
    assert remove_hidden.search(content)

    # Notes exist: no Generate, Edit and Remove shown.
    vintage.ai_tasting_notes = "Saved AI text"
    vintage.tasting_notes = "My own notes"
    vintage.save()
    for enabled in (False, True):
        with override_settings(AI_MODEL="m" if enabled else None, AI_API_KEY="k"):
            content = client.get(url).content.decode()
        assert "Saved AI text" in content
        assert "My own notes" in content
        assert "data-ai-generate" not in content
        assert ai_disabled_title not in content
        assert edit_url in content
        assert delete_url in content
        assert not remove_hidden.search(content)


@pytest.mark.django_db
def test_edit_replaces_notes_even_when_ai_disabled(client, user, vintage):
    vintage.ai_tasting_notes = "old text"
    vintage.save()
    client.force_login(user)
    url = reverse(
        "vintage-ai-tasting-notes-edit",
        kwargs={"wine_pk": vintage.wine_id, "pk": vintage.pk},
    )

    r = client.get(url)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].initial["ai_tasting_notes"] == "old text"

    r = client.post(url, {"ai_tasting_notes": "Pasted from elsewhere\nLine 2"})

    assert r.status_code == HTTPStatus.FOUND
    assert r.url == reverse("wine-detail", kwargs={"pk": vintage.wine_id})
    vintage.refresh_from_db()
    assert vintage.ai_tasting_notes == "Pasted from elsewhere\nLine 2"


@pytest.mark.django_db
def test_edit_other_users_vintage_returns_404(client, user_factory, vintage):
    client.force_login(user_factory())
    url = reverse(
        "vintage-ai-tasting-notes-edit",
        kwargs={"wine_pk": vintage.wine_id, "pk": vintage.pk},
    )
    assert client.get(url).status_code == HTTPStatus.NOT_FOUND
    assert (
        client.post(url, {"ai_tasting_notes": "hacked"}).status_code
        == HTTPStatus.NOT_FOUND
    )


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_cancelled_job_does_not_overwrite_notes(mock_completion, user, vintage):
    mock_completion.return_value = _mock_response("AI notes")
    vintage.ai_tasting_notes = "My own notes"
    vintage.save()

    generate_ai_tasting_notes(vintage.pk, user.pk, "job")

    vintage.refresh_from_db()
    assert vintage.ai_tasting_notes == "My own notes"
    assert wine_prefill_cache.get(ai_tasting_notes_cache_key(vintage.pk)) is None
