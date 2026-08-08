import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_login_page_renders_a_form(live_server, page):
    """Smoke test for the Playwright + Django `live_server` wiring itself -
    not app coverage. If this fails, something is wrong with the browser
    install or the live server, not with a specific feature."""
    response = page.goto(f"{live_server.url}{reverse('account_login')}")
    assert response.ok
    assert page.locator("form").count() > 0
