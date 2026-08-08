"""The real login/logout/signup/password-reset flows, driven through the
actual allauth forms (every other test file uses the fast ``login`` cookie
fixture instead - see tests/e2e/conftest.py)."""

import pytest
from django.core import mail
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_successful_login_redirects_to_homepage(live_server, page, user):
    page.goto(f"{live_server.url}{reverse('account_login')}")
    page.locator("#id_login").fill(user.username)
    page.locator("#id_password").fill("password")
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url(live_server.url + "/")
    assert (
        page.locator("nav.menu__md")
        .get_by_role("link", name="Wines", exact=True)
        .count()
        == 1
    )


@pytest.mark.django_db
def test_wrong_password_shows_error_and_stays_on_login_page(live_server, page, user):
    page.goto(f"{live_server.url}{reverse('account_login')}")
    page.locator("#id_login").fill(user.username)
    page.locator("#id_password").fill("not-the-password")
    page.get_by_role("button", name="Sign In").click()
    page.wait_for_url("**/accounts/login/**")
    assert page.locator(".form-errorlist, .errorlist").count() > 0


@pytest.mark.django_db
def test_logout_ends_the_session(live_server, page, login, user):
    login(user)
    page.goto(live_server.url)
    page.locator("nav.menu__md").get_by_role("button", name="Logout").click()
    page.locator("nav.menu__md").get_by_role(
        "link", name="Login", exact=True
    ).wait_for()

    # The session is really gone, not just the nav re-rendered: a protected
    # page now bounces back to login.
    page.goto(f"{live_server.url}{reverse('wine-list')}")
    page.wait_for_url("**/accounts/login/**")


@pytest.mark.django_db
def test_signup_is_closed_by_default(live_server, page):
    page.goto(f"{live_server.url}{reverse('account_signup')}")
    assert "Sign Up Closed" in page.locator("main").inner_text()
    assert page.locator("input[name='password1']").count() == 0


@pytest.mark.django_db
def test_password_reset_request_sends_an_email(live_server, page, user):
    page.goto(f"{live_server.url}{reverse('account_reset_password')}")
    page.locator("#id_email").fill(user.email)
    outbox_before = len(mail.outbox)
    page.get_by_role("button", name="Reset My Password").click()
    page.wait_for_url("**/accounts/password/reset/done/**")
    assert len(mail.outbox) == outbox_before + 1
    assert user.email in mail.outbox[-1].to
