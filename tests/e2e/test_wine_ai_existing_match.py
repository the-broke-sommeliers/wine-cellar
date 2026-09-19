"""Browser-level coverage for the AI duplicate-wine disambiguation page
(WineAiExistingMatchView, wine_ai_existing_match.html) - added so that
scanning a wine via AI that already exists in the cellar offers a clear
next step (add a vintage to it, or knowingly add it as a new wine) instead
of only failing at the very end of the create wizard.

Like tests/e2e/test_wine_scan_and_ai_disabled.py, this seeds the
`wine_prefill_cache` directly rather than driving a real `litellm` call
through the browser (LocMemCache's storage is shared across threads in the
same process, so a write here is visible to the live_server thread) - the
AI extraction/poll pipeline itself, including the duplicate-match redirect
branch, is already exhaustively covered with mocked `litellm.completion`
calls in tests/wine/test_views_ai.py. This file only exercises what a
mocked poll can't: the actual rendered page and the two choices it offers.
"""

import pytest
from django.core.cache import caches
from django.urls import reverse

from tests.e2e.conftest import tom_select_selected_text
from wine_cellar.apps.wine.models import Vintage, Wine

pytestmark = pytest.mark.e2e

wine_prefill_cache = caches["wine_prefill"]


def _seed_done_entry(token, user, initial, images=None):
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": initial,
            "images": images or {},
            "user_id": user.pk,
        },
        timeout=60,
    )


@pytest.mark.django_db
def test_existing_match_page_shows_matched_wine_and_offers_choices(
    live_server, page, login, user, wine_factory, size_factory
):
    size = size_factory(user=user, name=0.75)
    wine_factory(
        user=user, name="Chateau Test", wine_type="RE", size=size, country="DE"
    )
    token = "e2e-match-token"
    _seed_done_entry(
        token,
        user,
        {"name": "Chateau Test", "wine_type": "RE", "size": size.pk, "country": "DE"},
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('wine-ai-existing-match', kwargs={'token': token})}"
    )

    assert "This might already be in your cellar" in page.locator("main").inner_text()
    assert "Chateau Test" in page.locator("main").inner_text()
    assert page.get_by_role("link", name="Yes, add a new vintage to it").count() == 1
    assert page.get_by_role("link", name="No, add as a new wine").count() == 1


@pytest.mark.django_db
def test_choosing_add_vintage_prefills_and_saves_a_new_vintage(
    live_server, page, login, user, wine_factory, size_factory
):
    size = size_factory(user=user, name=0.75)
    wine = wine_factory(
        user=user,
        name="Chateau Test",
        wine_type="RE",
        size=size,
        country="DE",
        _create_default_vintage=False,
    )
    token = "e2e-match-token-vintage"
    _seed_done_entry(
        token,
        user,
        {
            "name": "Chateau Test",
            "wine_type": "RE",
            "size": size.pk,
            "country": "DE",
            "year": 2021,
            "abv": 13.5,
            "barcode": "1112223334445",
        },
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('wine-ai-existing-match', kwargs={'token': token})}"
    )
    page.get_by_role("link", name="Yes, add a new vintage to it").click()
    page.wait_for_url(f"**{reverse('vintage-add', kwargs={'wine_pk': wine.pk})}**")

    assert page.locator("#id_year").input_value() == "2021"
    assert page.locator("#id_abv").input_value() == "13.5"
    assert page.locator("#id_barcode").input_value() == "1112223334445"

    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}**")

    vintage = Vintage.objects.get(wine=wine, year=2021)
    assert vintage.abv == 13.5
    assert vintage.barcode == "1112223334445"
    # The token must be consumed on a successful save - it's single-use.
    assert wine_prefill_cache.get(f"wine_prefill_{token}") is None


@pytest.mark.django_db
def test_choosing_add_as_new_wine_prefills_and_can_save_after_changing_a_field(
    live_server, page, login, user, wine_factory, size_factory
):
    size = size_factory(user=user, name=0.75)
    wine_factory(
        user=user, name="Chateau Test", wine_type="RE", size=size, country="DE"
    )
    token = "e2e-match-token-new-wine"
    _seed_done_entry(
        token,
        user,
        {"name": "Chateau Test", "wine_type": "RE", "size": size.pk, "country": "DE"},
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('wine-ai-existing-match', kwargs={'token': token})}"
    )
    page.get_by_role("link", name="No, add as a new wine").click()
    page.wait_for_url(f"**{reverse('wine-add')}**")

    assert page.locator("#id_name").input_value() == "Chateau Test"
    assert tom_select_selected_text(page, "id_wine_type") == ["Red"]
    assert tom_select_selected_text(page, "id_country") == ["Germany"]

    # Saving unchanged would collide with the existing wine - the whole
    # point of this path is that the user must change something first.
    page.locator("#id_name").fill("Chateau Test - Second Bottle")
    for next_step in range(1, 6):
        page.get_by_role("button", name="Continue").click()
        page.wait_for_selector(f"#create__fs_{next_step}:not(.hidden)")

    page.get_by_role("button", name="Save and Finish").click()
    page.wait_for_url(f"**{reverse('wine-list')}")

    assert Wine.objects.filter(user=user, name="Chateau Test - Second Bottle").exists()


@pytest.mark.django_db
def test_existing_match_page_flags_colliding_vintage_year(
    live_server, page, login, user, wine_factory, vintage_factory, size_factory
):
    size = size_factory(user=user, name=0.75)
    wine = wine_factory(
        user=user,
        name="Chateau Test",
        wine_type="RE",
        size=size,
        country="DE",
        _create_default_vintage=False,
    )
    vintage_factory(wine=wine, year=2020)
    token = "e2e-match-token-year-collision"
    _seed_done_entry(
        token,
        user,
        {
            "name": "Chateau Test",
            "wine_type": "RE",
            "size": size.pk,
            "country": "DE",
            "year": 2020,
        },
    )
    login(user)
    page.goto(
        f"{live_server.url}{reverse('wine-ai-existing-match', kwargs={'token': token})}"
    )
    assert "already have a 2020 vintage" in page.locator("main").inner_text()
