"""Wine detail page rendering (WineDetailView, wine_detail.html):
populated fields, drink-by warning, placeholder image, and the
multi-image carousel (assets/js/wine_carousel.ts)."""

import datetime

import pytest
from django.urls import reverse

from wine_cellar.apps.wine.models import ImageType

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_detail_page_shows_populated_fields(
    live_server,
    page,
    login,
    user,
    wine_factory,
    vintage_factory,
    grape_factory,
    region_factory,
):
    grape = grape_factory(name="Riesling")
    region = region_factory(name="Mosel")
    wine = wine_factory(
        user=user,
        name="Detailed Wine",
        grapes=[grape],
        region=region,
        _create_default_vintage=False,
    )
    vintage_factory(wine=wine, price=25, rating=9)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    detail_text = page.locator("main").inner_text()
    assert "Detailed Wine" in detail_text
    assert "Riesling" in detail_text
    assert "Mosel" in detail_text
    assert "9/10" in detail_text


@pytest.mark.django_db
def test_drink_by_warning_icon_shown_only_when_due_soon(
    live_server, page, login, user, wine_factory, vintage_factory
):
    today = datetime.date.today()
    due_soon = wine_factory(
        user=user, name="Drink Me Soon", _create_default_vintage=False
    )
    vintage_factory(wine=due_soon, drink_by=today)
    not_due = wine_factory(user=user, name="Not Yet", _create_default_vintage=False)
    vintage_factory(wine=not_due, drink_by=today + datetime.timedelta(days=60))
    login(user)

    page.goto(f"{live_server.url}{reverse('wine-detail', kwargs={'pk': due_soon.pk})}")
    assert page.locator(".wine-card__drink-warning").count() == 1

    page.goto(f"{live_server.url}{reverse('wine-detail', kwargs={'pk': not_due.pk})}")
    assert page.locator(".wine-card__drink-warning").count() == 0


@pytest.mark.django_db
def test_wine_without_images_shows_placeholder_bottle(
    live_server, page, login, user, wine_factory
):
    wine = wine_factory(user=user, name="No Photos")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    image_src = page.locator("#wine-image").get_attribute("src")
    assert "bottle.svg" in image_src
    # The controls div is always rendered now (so JS can reveal it on a
    # vintage-tab switch), just hidden when there's nothing to cycle through.
    assert page.locator(".image-controls").is_hidden()


@pytest.mark.django_db
def test_carousel_controls_appear_and_cycle_with_multiple_images(
    live_server, page, login, user, wine_factory, wine_image_factory, clear_image_folder
):
    wine = wine_factory(user=user, name="Two Photos")
    vintage = wine.latest_vintage
    front = wine_image_factory(vintage=vintage, user=user, image_type=ImageType.FRONT)
    wine_image_factory(vintage=vintage, user=user, image_type=ImageType.BACK)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    prev_btn = page.locator(".wine-prev")
    next_btn = page.locator(".wine-next")
    assert prev_btn.count() == 1
    assert prev_btn.is_disabled()
    assert not next_btn.is_disabled()

    first_src = page.locator("#wine-image").get_attribute("src")
    assert front.thumbnail.url in first_src or front.image.url in first_src

    next_btn.click()
    assert prev_btn.is_enabled()
    assert next_btn.is_disabled()
    second_src = page.locator("#wine-image").get_attribute("src")
    assert second_src != first_src

    prev_btn.click()
    assert page.locator("#wine-image").get_attribute("src") == first_src
