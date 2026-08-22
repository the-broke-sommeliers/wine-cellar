"""Homepage dashboard: stat cards and their deep links into the wine list
(wine_cellar/apps/wine/views.py:35-99, templates/homepage.html)."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


def stat_cards(page):
    return page.locator("ul.stats__card-container li.stats__card")


@pytest.mark.django_db
def test_homepage_stats_are_empty_for_a_fresh_user(live_server, page, login, user):
    login(user)
    page.goto(live_server.url)
    cards = stat_cards(page)
    # order: Recorded Wines, Wines in Stock, Bottles in Stock, Countries,
    # Total Value, Oldest Wine, Youngest Wine
    assert cards.nth(0).locator(".stats__number").inner_text() == "0"
    assert cards.nth(1).locator(".stats__number").inner_text() == "0"
    assert cards.nth(2).locator(".stats__number").inner_text() == "0"
    assert cards.nth(3).locator(".stats__number").inner_text() == "0"
    assert "0" in cards.nth(4).locator(".stats__number").inner_text()
    assert cards.nth(5).locator(".stats__number").inner_text() == "-"
    assert cards.nth(6).locator(".stats__number").inner_text() == "-"


@pytest.mark.django_db
def test_homepage_stats_reflect_data_and_deep_link_into_wine_list(
    live_server,
    page,
    login,
    user,
    wine_factory,
    vintage_factory,
    storage_factory,
    storage_item_factory,
):
    wine_old = wine_factory(user=user, country="DE", _create_default_vintage=False)
    vintage_old = vintage_factory(wine=wine_old, year=1950)
    wine_new = wine_factory(user=user, country="FR", _create_default_vintage=False)
    vintage_factory(wine=wine_new, year=2020)
    storage = storage_factory(user=user, rows=0, columns=0)
    storage_item_factory(vintage=vintage_old, storage=storage, user=user, price=10)

    login(user)
    page.goto(live_server.url)
    cards = stat_cards(page)

    assert cards.nth(0).locator(".stats__number").inner_text() == "2"  # Recorded
    assert cards.nth(1).locator(".stats__number").inner_text() == "1"  # Wines in stock
    assert cards.nth(2).locator(".stats__number").inner_text() == "1"  # Bottles
    assert cards.nth(3).locator(".stats__number").inner_text() == "2"  # Countries
    assert cards.nth(5).locator(".stats__number").inner_text() == "1950"  # Oldest
    assert cards.nth(6).locator(".stats__number").inner_text() == "2020"  # Youngest

    # "Wines in Stock" deep-links to wine-list?stock=1 and actually filters.
    cards.nth(1).locator("a.stats__link").click()
    page.wait_for_url(f"**{reverse('wine-list')}?stock=1")
    cards_on_list = page.locator("ul.wine-card__list li.wine-card")
    assert cards_on_list.count() == 1
    assert wine_old.name in cards_on_list.inner_text()

    # "Oldest Wine" deep-links with order=vintage_year and the oldest wine sorts first.
    page.goto(live_server.url)
    stat_cards(page).nth(5).locator("a.stats__link").click()
    page.wait_for_url("**order=vintage_year**")
    first_card = page.locator("ul.wine-card__list li.wine-card").first
    assert wine_old.name in first_card.inner_text()
