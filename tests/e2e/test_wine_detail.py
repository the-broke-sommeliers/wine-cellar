"""Wine detail page rendering (WineDetailView, wine_detail.html):
populated fields, drink-by warning, placeholder image, and the
multi-image carousel (assets/js/wine_carousel.ts)."""

import datetime

import pytest
from django.urls import reverse

from wine_cellar.apps.wine.models import ImageType, WineTastingNote

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


@pytest.mark.django_db
def test_tasting_notes_show_text_before_metadata_and_actions(
    live_server, page, login, user, wine_factory
):
    wine = wine_factory(user=user, name="Tasting Notes Wine")
    vintage = wine.latest_vintage
    general_note = WineTastingNote.objects.create(
        wine=wine, user=user, note="A general tasting", rating=0
    )
    WineTastingNote.objects.create(
        wine=wine, user=user, vintage=vintage, note="A vintage tasting", rating=5
    )
    login(user)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server.url}{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    notes = page.locator(".tasting-note")
    assert notes.count() == 2
    general = notes.filter(has_text="A general tasting")
    specific = notes.filter(has_text="A vintage tasting")
    assert general.get_by_text("Vintage", exact=True).count() == 0
    assert "0/5" in general.inner_text()
    assert str(vintage.year) in specific.inner_text()
    assert "5/5" in specific.inner_text()
    assert notes.nth(1).bounding_box()["y"] >= (
        notes.nth(0).bounding_box()["y"] + notes.nth(0).bounding_box()["height"]
    )
    note_text = specific.locator(".tasting-note__text")
    vintage_label = specific.get_by_text("Vintage", exact=True)
    score_label = specific.get_by_text("Score", exact=True)
    date = specific.locator(".tasting-note__date")
    specific_delete = specific.get_by_role("link", name="Delete", exact=True)
    assert note_text.bounding_box()["y"] < vintage_label.bounding_box()["y"]
    assert vintage_label.bounding_box()["y"] == score_label.bounding_box()["y"]
    assert vintage_label.evaluate(
        "element => parseFloat(getComputedStyle(element).fontSize)"
    ) < note_text.evaluate("element => parseFloat(getComputedStyle(element).fontSize)")
    for width in (320, 768, 1280):
        page.set_viewport_size({"width": width, "height": 844})
        vintage_box = vintage_label.bounding_box()
        score_box = score_label.bounding_box()
        date_box = date.bounding_box()
        header_box = specific.locator(".tasting-note__header").bounding_box()
        assert vintage_box["y"] == score_box["y"]
        assert score_box["x"] > vintage_box["x"] + vintage_box["width"]
        assert date_box["y"] == header_box["y"]
        assert (
            abs(
                header_box["x"]
                + header_box["width"]
                - date_box["x"]
                - date_box["width"]
            )
            < 1
        )
        footer_box = specific.locator(".tasting-note__footer").bounding_box()
        delete_box = specific_delete.bounding_box()
        assert (
            abs(
                footer_box["x"]
                + footer_box["width"]
                - delete_box["x"]
                - delete_box["width"]
            )
            < 1
        )
        metadata_box = specific.locator(".tasting-note__metadata").bounding_box()
        assert (
            abs(
                metadata_box["y"]
                + metadata_box["height"]
                - delete_box["y"]
                - delete_box["height"]
            )
            < 1
        )

    delete = general.get_by_role("link", name="Delete", exact=True)
    assert delete.is_visible()
    assert general.get_by_role("link", name="Edit", exact=True).count() == 0
    assert general.locator("details").count() == 0
    assert delete.get_attribute("href") == reverse(
        "wine-tasting-note-delete", kwargs={"wine_pk": wine.pk, "pk": general_note.pk}
    )
    assert specific.get_by_role("link", name="Edit", exact=True).count() == 0
    assert specific_delete.is_visible()
    delete.click()
    assert page.get_by_role("heading", name="Delete Tasting Note").is_visible()
