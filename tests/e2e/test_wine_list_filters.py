"""Wine list filtering/ordering/pagination (WineListView + WineFilter,
wine_cellar/apps/wine/filters.py, template wine_list.html).

The filter form is rendered twice in the template (a `<details>`-wrapped
copy for small screens, an always-open copy for large screens), toggled
purely by CSS media queries - both get real ids. At the default desktop
viewport only `.filter-form--lg` is visible, so plain field interactions
are scoped to it explicitly (`tom_select_pick` already filters `:visible`
internally for the tom-select fields).
"""

import pytest
from django.urls import reverse

from tests.e2e.conftest import tom_select_pick

pytestmark = pytest.mark.e2e


def visible_filter_form(page):
    return page.locator(".filter-form--lg")


@pytest.mark.django_db
def test_name_filter_narrows_results(live_server, page, login, user, wine_factory):
    wine_factory(user=user, name="Chateau Margaux")
    wine_factory(user=user, name="Opus One")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-list')}")

    visible_filter_form(page).locator("#id_name").fill("Margaux")
    visible_filter_form(page).get_by_role("button", name="Filter", exact=True).click()
    page.wait_for_url("**name=Margaux**")

    cards = page.locator("ul.wine-card__list li.wine-card")
    assert cards.count() == 1
    assert "Chateau Margaux" in cards.inner_text()


@pytest.mark.django_db
def test_stock_yes_filter_shows_only_wines_in_stock(
    live_server, page, login, user, wine_factory, storage_factory, storage_item_factory
):
    in_stock = wine_factory(user=user, name="In Stock Wine")
    wine_factory(user=user, name="Not In Stock Wine")
    storage = storage_factory(user=user, rows=0, columns=0)
    storage_item_factory(wine=in_stock, storage=storage, user=user)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-list')}")

    tom_select_pick(page, "id_stock", "Yes")
    visible_filter_form(page).get_by_role("button", name="Filter", exact=True).click()
    page.wait_for_url("**stock=1**")

    cards = page.locator("ul.wine-card__list li.wine-card")
    assert cards.count() == 1
    assert "In Stock Wine" in cards.inner_text()


@pytest.mark.django_db
def test_wine_type_filter(live_server, page, login, user, wine_factory):
    wine_factory(user=user, name="Red Wine", wine_type="RE")
    wine_factory(user=user, name="White Wine", wine_type="WH")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-list')}")

    tom_select_pick(page, "id_wine_type", "Red")
    visible_filter_form(page).get_by_role("button", name="Filter", exact=True).click()
    page.wait_for_url("**wine_type=RE**")

    cards = page.locator("ul.wine-card__list li.wine-card")
    assert cards.count() == 1
    assert "Red Wine" in cards.inner_text()


@pytest.mark.django_db
def test_order_by_name_ascending(live_server, page, login, user, wine_factory):
    wine_factory(user=user, name="Zinfandel")
    wine_factory(user=user, name="Albarino")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-list')}")

    tom_select_pick(page, "id_order", "Name Ascending")
    visible_filter_form(page).get_by_role("button", name="Filter", exact=True).click()
    page.wait_for_url("**order=name**")

    first_card = page.locator("ul.wine-card__list li.wine-card").first
    assert "Albarino" in first_card.inner_text()


@pytest.mark.django_db
def test_clear_link_resets_filters(live_server, page, login, user, wine_factory):
    wine_factory(user=user, name="Only Wine")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-list')}?name=nomatch")
    assert page.locator("ul.wine-card__list li.wine-card").count() == 0

    # `role="button"` is set explicitly on this `<a>`, overriding its
    # implicit "link" role.
    visible_filter_form(page).get_by_role("button", name="Clear all filters").click()
    page.locator("ul.wine-card__list li.wine-card").first.wait_for()
    assert page.locator("ul.wine-card__list li.wine-card").count() == 1


@pytest.mark.django_db
def test_pagination_across_multiple_pages(live_server, page, login, user, wine_factory):
    for i in range(12):
        wine_factory(user=user, name=f"Wine {i:02d}")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-list')}")

    assert page.locator("ul.wine-card__list li.wine-card").count() == 10
    assert page.locator("ul.pagination li").count() >= 3  # prev, 1, 2, next

    page.locator("ul.pagination a", has_text="2").click()
    page.wait_for_url("**page=2**")
    assert page.locator("ul.wine-card__list li.wine-card").count() == 2
