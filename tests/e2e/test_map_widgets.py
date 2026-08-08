"""Map widgets (react_maps_tags.py + wine_cellar/react/maps/*) mount their
container elements correctly. Headless Chromium here has no GPU, so
MapLibre GL (WebGL-based) cannot actually render tiles or accept map
clicks - these tests only check that the app wires up the right container
for each widget, not that tile imagery loads or that clicking places a
marker, which would need a real GPU/network."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_wine_list_map_mounts(
    live_server, page, login, user, wine_factory, geojson_point
):
    wine_factory(user=user, name="Located Wine", location=geojson_point)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-map')}")
    assert page.locator("#wine_map").count() == 1


@pytest.mark.django_db
def test_wine_detail_map_mounts_only_when_wine_has_a_location(
    live_server, page, login, user, wine_factory, geojson_point
):
    with_location = wine_factory(user=user, name="Placed Wine", location=geojson_point)
    without_location = wine_factory(user=user, name="Unplaced Wine")
    login(user)

    page.goto(
        f"{live_server.url}{reverse('wine-detail', kwargs={'pk': with_location.pk})}"
    )
    assert page.locator("#wine_map").count() == 1

    page.goto(
        f"{live_server.url}{reverse('wine-detail', kwargs={'pk': without_location.pk})}"
    )
    assert page.locator("#wine_map").count() == 0


@pytest.mark.django_db
def test_choose_point_widget_mounts_on_create_form(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add')}")
    assert page.locator("#map_select_point").count() == 1
    assert page.locator("#id_location").count() == 1
