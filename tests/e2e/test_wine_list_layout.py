"""Wine list layout driven by the "Wines per Row" and "Compact Wine List"
user settings (card.css / forms.css). The column counts and card widths come
from CSS grid math, so only a real browser can check them."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e

WIDE_VIEWPORT = {"width": 2600, "height": 1200}


def first_row_columns(page):
    return page.evaluate("""() => {
            const cards = [...document.querySelectorAll("li.wine-card")];
            const top = cards[0].getBoundingClientRect().top;
            return cards.filter(
                (c) => Math.abs(c.getBoundingClientRect().top - top) < 1
            ).length;
        }""")


def side_gaps(page):
    """Space left of the filter bar and right of the card list, measured
    from .main's content box."""
    return page.evaluate("""() => {
            const main = document.querySelector(".main");
            const box = main.getBoundingClientRect();
            const style = getComputedStyle(main);
            const filter = document.querySelector(".wine-list__filter-col");
            const results = document.querySelector(".wine-list__results-col");
            return [
                filter.getBoundingClientRect().left
                    - (box.left + parseFloat(style.paddingLeft)),
                box.right - parseFloat(style.paddingRight)
                    - results.getBoundingClientRect().right,
            ];
        }""")


def open_wine_list(live_server, page, login, user):
    login(user)
    page.set_viewport_size(WIDE_VIEWPORT)
    page.goto(f"{live_server.url}{reverse('wine-list')}")


@pytest.mark.django_db
def test_wines_per_row_caps_columns(
    live_server, page, login, user, user_settings_factory, wine_factory
):
    for i in range(8):
        wine_factory(user=user, name=f"Wine {i}")
    settings = user_settings_factory(user=user)

    open_wine_list(live_server, page, login, user)
    automatic_columns = first_row_columns(page)
    assert automatic_columns > 3

    settings.max_wines_per_row = 3
    settings.save()
    page.reload()
    assert first_row_columns(page) == 3


@pytest.mark.django_db
@pytest.mark.parametrize("compact", [True, False])
def test_compact_wine_list_limits_card_width(
    live_server, page, login, user, user_settings_factory, wine_factory, compact
):
    # A cap of 2 on a wide screen would stretch the cards well past their
    # compact maximum (420px, --card-max-width in card.css).
    user_settings_factory(user=user, max_wines_per_row=2, compact_wine_list=compact)
    for i in range(4):
        wine_factory(user=user, name=f"Wine {i}")

    open_wine_list(live_server, page, login, user)
    card_width = page.locator("li.wine-card").first.bounding_box()["width"]
    left_gap, right_gap = side_gaps(page)

    if compact:
        assert card_width == pytest.approx(420, abs=1)
        assert left_gap > 100
        assert left_gap == pytest.approx(right_gap, abs=1)
    else:
        assert card_width > 420
        assert left_gap == pytest.approx(0, abs=1)
        assert right_gap == pytest.approx(0, abs=1)
