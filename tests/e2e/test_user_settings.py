"""User settings (UserSettingsView, wine_cellar/apps/user/), the sidebar
shared with allauth's account-management pages, and the language-cookie
side effect of saving a new language."""

import pytest
from django.urls import reverse

from tests.e2e.conftest import tom_select_pick

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_settings_save_and_persist(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('user-settings')}")

    tom_select_pick(page, "id_currency", "Dollar")
    page.locator("#id_notifications").uncheck()
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('user-settings')}")
    assert page.eval_on_selector("#id_currency", "el => el.value") == "USD"
    assert not page.locator("#id_notifications").is_checked()

    page.reload()
    assert page.eval_on_selector("#id_currency", "el => el.value") == "USD"
    assert not page.locator("#id_notifications").is_checked()

    user.user_settings.refresh_from_db()
    assert user.user_settings.currency == "USD"
    assert user.user_settings.notifications is False


@pytest.mark.django_db
def test_changing_language_translates_subsequent_pages(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('user-settings')}")

    tom_select_pick(page, "id_language", "German")
    page.get_by_role("button", name="Save").click()
    page.wait_for_url(f"**{reverse('user-settings')}")

    page.goto(live_server.url)
    assert "Weine" in page.locator("nav.menu__md").inner_text()


@pytest.mark.django_db
def test_settings_sidebar_highlights_active_tab(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('user-settings')}")
    sidebar = page.locator(".settings-sidebar")
    assert "pure-menu-selected" in sidebar.locator(
        "li", has_text="General Settings"
    ).get_attribute("class")
    assert "pure-menu-selected" not in (
        sidebar.locator("li", has_text="Email Addresses").get_attribute("class") or ""
    )


@pytest.mark.django_db
def test_allauth_manage_pages_reachable_from_sidebar(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('user-settings')}")

    page.locator(".settings-sidebar").get_by_role(
        "link", name="Email Addresses"
    ).click()
    page.wait_for_url(f"**{reverse('account_email')}")
    assert "Email Addresses" in page.locator("main").inner_text()

    page.locator(".settings-sidebar").get_by_role(
        "link", name="Change Password"
    ).click()
    page.wait_for_url(f"**{reverse('account_change_password')}")
    assert page.locator("input[name='oldpassword']").count() == 1
