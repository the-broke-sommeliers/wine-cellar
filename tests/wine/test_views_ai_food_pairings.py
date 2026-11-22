import re
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.urls import reverse

from wine_cellar.apps.wine.models import FoodPairing, Size
from wine_cellar.apps.wine.tasks import (
    _clean_food_pairing_names,
    _get_or_create_food_pairing,
    generate_ai_food_pairings,
)
from wine_cellar.apps.wine.utils import ai_food_pairings_cache_key, wine_prefill_cache

ai_settings = override_settings(AI_MODEL="test-model", AI_API_KEY="test-key")


def _mock_response(content):
    resp = MagicMock()
    resp.choices[0].message.content = content
    return resp


def _urls(wine):
    return (
        reverse("wine-ai-food-pairings", kwargs={"pk": wine.pk}),
        reverse("wine-ai-food-pairings-poll", kwargs={"pk": wine.pk}),
        reverse("wine-food-pairings-delete", kwargs={"pk": wine.pk}),
    )


@pytest.fixture
def wine(user, wine_factory, grape_factory, region_factory):
    return wine_factory(
        user=user,
        name="Barolo Riserva",
        country="IT",
        region=region_factory(name="Piedmont", user=user),
        grapes=[grape_factory(name="Nebbiolo", user=user)],
    )


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_generate_adds_new_and_reuses_existing_pairings(
    mock_completion, client, user, user_factory, wine, food_pairing_factory
):
    own = food_pairing_factory(name="Roast Lamb", user=user)
    shared = food_pairing_factory(name="Truffle risotto", user=None)
    foreign = food_pairing_factory(name="Ossobuco", user=user_factory())
    mock_completion.return_value = _mock_response(
        '```json\n{"food_pairings": ["roast lamb", "Truffle risotto",'
        ' "Ossobuco", " Aged Parmesan ", "aged parmesan"]}\n```'
    )
    client.force_login(user)
    generate_url, poll_url, _ = _urls(wine)

    r = client.post(generate_url)
    assert r.status_code == HTTPStatus.OK
    assert r.json()["poll_url"] == poll_url

    pairings = set(wine.food_pairings.all())
    new_ossobuco = FoodPairing.objects.get(name="Ossobuco", user=user)
    parmesan = FoodPairing.objects.get(name="Aged Parmesan", user=user)
    assert pairings == {own, shared, new_ossobuco, parmesan}
    assert foreign not in pairings

    data = client.get(poll_url).json()
    assert data["status"] == "done"
    assert set(data["items"]) == {
        "Roast Lamb",
        "Truffle risotto",
        "Ossobuco",
        "Aged Parmesan",
    }

    prompt = mock_completion.call_args.kwargs["messages"][0]["content"]
    for expected in ("Barolo Riserva", "Nebbiolo", "Piedmont", "Italy"):
        assert expected in prompt
    assert '"Roast Lamb"' in prompt
    assert '"Truffle risotto"' in prompt
    assert "Ossobuco" not in prompt


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_generate_invalid_response_is_error(mock_completion, client, user, wine):
    mock_completion.return_value = _mock_response("Lamb, cheese and mushrooms")
    client.force_login(user)
    generate_url, poll_url, _ = _urls(wine)

    client.post(generate_url)

    data = client.get(poll_url).json()
    assert data["status"] == "error"
    assert not wine.food_pairings.exists()


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_other_users_wine_returns_404(
    mock_completion, client, user_factory, wine, food_pairing_factory
):
    wine.food_pairings.add(food_pairing_factory(name="Lamb", user=wine.user))
    client.force_login(user_factory())
    generate_url, poll_url, delete_url = _urls(wine)

    assert client.post(generate_url).status_code == HTTPStatus.NOT_FOUND
    assert client.get(poll_url).status_code == HTTPStatus.NOT_FOUND
    assert client.post(delete_url).status_code == HTTPStatus.NOT_FOUND
    mock_completion.assert_not_called()
    assert wine.food_pairings.count() == 1


@pytest.mark.django_db
def test_generate_and_poll_404_when_ai_disabled(client, user, wine):
    client.force_login(user)
    generate_url, poll_url, _ = _urls(wine)
    assert client.post(generate_url).status_code == HTTPStatus.NOT_FOUND
    assert client.get(poll_url).status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_delete_clears_pairings_but_keeps_objects(
    client, user, wine, food_pairing_factory
):
    pairing = food_pairing_factory(name="Lamb", user=user)
    wine.food_pairings.add(pairing)
    client.force_login(user)
    _, _, delete_url = _urls(wine)

    r = client.post(delete_url)

    assert r.status_code == HTTPStatus.FOUND
    assert r.url == reverse("wine-detail", kwargs={"pk": wine.pk})
    assert not wine.food_pairings.exists()
    assert FoodPairing.objects.filter(pk=pairing.pk).exists()


@pytest.mark.django_db
def test_detail_page_food_pairings_box(client, user, wine, food_pairing_factory):
    client.force_login(user)
    url = reverse("wine-detail", kwargs={"pk": wine.pk})
    generate_url, _, delete_url = _urls(wine)
    edit_url = reverse("wine-edit", kwargs={"pk": wine.pk}) + "#field-food_pairings"
    remove_hidden = re.compile(rf'action="{delete_url}"\s+class="hidden"')

    content = client.get(url).content.decode()
    assert "AI is not configured on this server." in content
    assert f'data-ai-generate="{generate_url}"' not in content
    assert edit_url in content
    assert remove_hidden.search(content)

    with ai_settings:
        content = client.get(url).content.decode()
    assert f'data-ai-generate="{generate_url}"' in content

    wine.food_pairings.add(food_pairing_factory(name="Roast lamb", user=user))
    with ai_settings:
        content = client.get(url).content.decode()
    assert '<li class="ai-box__item">Roast lamb</li>' in content
    assert f'data-ai-generate="{generate_url}"' not in content
    assert edit_url in content
    assert delete_url in content
    assert not remove_hidden.search(content)


def test_clean_food_pairing_names():
    assert _clean_food_pairing_names("Lamb") == []
    assert _clean_food_pairing_names([" Lamb ", "lamb", "", 3, "Cheese"]) == [
        "Lamb",
        "Cheese",
    ]
    assert len(_clean_food_pairing_names([f"Dish {i}" for i in range(20)])) == 8


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_superseded_job_does_not_add_pairings(mock_completion, user, wine):
    mock_completion.return_value = _mock_response('{"food_pairings": ["Roast lamb"]}')
    cache_key = ai_food_pairings_cache_key(wine.pk)
    newer = {"status": "pending", "user_id": user.pk, "job_id": "newer"}
    wine_prefill_cache.set(cache_key, newer)

    generate_ai_food_pairings(wine.pk, user.pk, "older")

    assert not wine.food_pairings.exists()
    assert wine_prefill_cache.get(cache_key) == newer


@pytest.mark.django_db
def test_wine_edit_cancels_pending_job(client, user, wine):
    cache_key = ai_food_pairings_cache_key(wine.pk)
    wine_prefill_cache.set(cache_key, {"status": "pending", "user_id": user.pk})
    client.force_login(user)
    data = {
        "name": wine.name,
        "wine_type": "RE",
        "category": "DR",
        "size": Size.objects.get(name=0.75).pk,
        "year": 2002,
        "country": "DE",
    }

    r = client.post(reverse("wine-edit", kwargs={"pk": wine.pk}), data)

    assert r.status_code == HTTPStatus.FOUND
    assert wine_prefill_cache.get(cache_key) is None


@pytest.mark.django_db
def test_get_or_create_food_pairing_handles_concurrent_insert(user):
    existing = FoodPairing.objects.create(name="Roast lamb", user=user)

    pairing = _get_or_create_food_pairing(
        FoodPairing.objects.none(), "Roast lamb", user.pk
    )

    assert pairing == existing


@pytest.mark.django_db
@ai_settings
@patch("litellm.completion")
def test_unexpected_error_sets_error_status(mock_completion, client, user, wine):
    mock_completion.side_effect = RuntimeError("boom")
    client.force_login(user)
    generate_url, poll_url, _ = _urls(wine)

    client.post(generate_url)

    data = client.get(poll_url).json()
    assert data["status"] == "error"
    assert data["message"] == "The AI request failed. Please try again."
