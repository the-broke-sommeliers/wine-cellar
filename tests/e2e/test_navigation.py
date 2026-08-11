"""Global auth-gate and nav-link coverage.

``LoginRequiredMiddleware`` (wine_cellar/conf/settings.py) protects every
view except ``health_check`` - these tests assert that guarantee holds for
the main entry points, and that the logged-in nav actually goes where it
says it does.
"""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name", ["homepage", "wine-list", "storage-list", "wine-map", "user-settings"]
)
def test_protected_pages_redirect_anonymous_users_to_login(live_server, page, url_name):
    page.goto(f"{live_server.url}{reverse(url_name)}")
    page.wait_for_url("**/accounts/login/**")
    assert page.locator("form").count() > 0


@pytest.mark.django_db
def test_health_check_does_not_require_login(live_server, page):
    response = page.goto(f"{live_server.url}{reverse('health_check')}")
    assert response.ok
    assert "ok" in response.text()


@pytest.mark.django_db
def test_logged_in_nav_links_go_to_the_right_pages(live_server, page, login, user):
    login(user)
    page.goto(live_server.url)

    nav = page.locator("nav.menu__md")
    links = {
        "Wines": "wine-list",
        "Add Wine": "wine-add-choose",
        "Scan Wine": "wine-scan",
        "Map": "wine-map",
        "Storage": "storage-list",
        "Settings": "user-settings",
    }
    for text, url_name in links.items():
        nav.get_by_role("link", name=text, exact=True).click()
        page.wait_for_url(f"**{reverse(url_name)}")
        page.go_back()
        page.wait_for_url(live_server.url + "/")


@pytest.mark.django_db
def test_brand_link_returns_home(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-list')}")
    page.locator("nav.menu__md").get_by_role("link", name="Wine Cellar").click()
    page.wait_for_url(live_server.url + "/")


@pytest.mark.django_db
def test_footer_shows_version(live_server, page, login, user):
    login(user)
    page.goto(live_server.url)
    assert "Version" in page.locator("footer").inner_text()


@pytest.mark.django_db
def test_admin_link_visible_to_staff_and_hidden_from_regular_users(
    live_server, page, login, user
):
    login(user)
    page.goto(live_server.url)
    nav = page.locator("nav.menu__md")
    assert nav.get_by_role("link", name="Django Admin").count() == 0

    user.is_staff = True
    user.save(update_fields=["is_staff"])
    login(user)
    page.goto(live_server.url)
    nav = page.locator("nav.menu__md")
    admin_link = nav.get_by_role("link", name="Django Admin")
    assert admin_link.count() == 1
    admin_link.click()
    page.wait_for_url("**/admin/**")


@pytest.mark.django_db
def test_nav_shows_login_link_when_logged_out_and_full_menu_when_logged_in(
    live_server, page, login, user
):
    page.goto(live_server.url)
    nav = page.locator("nav.menu__md")
    assert nav.get_by_role("link", name="Login", exact=True).count() == 1
    assert nav.get_by_role("link", name="Wines", exact=True).count() == 0

    login(user)
    page.goto(live_server.url)
    nav = page.locator("nav.menu__md")
    assert nav.get_by_role("link", name="Wines", exact=True).count() == 1
    assert nav.get_by_role("button", name="Logout").count() == 1
    assert nav.get_by_role("link", name="Login", exact=True).count() == 0
