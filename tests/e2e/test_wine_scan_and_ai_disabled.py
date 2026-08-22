"""Barcode scan pages (WineScanView/WineScannedView) and the AI-upload
entry points with AI left unconfigured (the default in
`wine_cellar.conf.test` - neither AI_MODEL nor AI_API_KEY is set). The AI
success/error flows themselves are already exhaustively covered with
mocked `litellm.completion` calls in tests/wine/test_views_ai.py; driving
that through a real browser would mean mocking mid-request against
live_server, which is fragile and would only duplicate that coverage."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_scan_page_mounts_scanner_ui_without_a_camera(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-scan')}")

    # data-auto-open="true" on this page - the scanner starts open.
    close_btn = page.get_by_role("button", name="Close Scanner")
    assert close_btn.count() == 1

    page.get_by_text("Advanced").click()
    assert "Choose the type of barcode" in page.locator("main").inner_text()
    assert page.locator("select.scanner-format-select").count() == 1

    close_btn.click()
    assert page.get_by_role("button", name="Scan Barcode").count() == 1


@pytest.mark.django_db
def test_scanning_a_known_barcode_redirects_to_its_wine(
    live_server, page, login, user, wine_factory, vintage_factory
):
    wine = wine_factory(user=user, name="Scanned Wine", _create_default_vintage=False)
    vintage_factory(wine=wine, barcode="1234567890123")
    login(user)
    page.goto(f"{live_server.url}/wine/scan/1234567890123")
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    assert "Scanned Wine" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_scanning_an_unknown_barcode_offers_to_add_it(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}/wine/scan/9999999999999")

    assert "9999999999999" in page.locator("main").inner_text()
    page.get_by_role("link", name="Add new wine").click()
    page.wait_for_url("**barcode=9999999999999**")
    assert "wine-choose__card--disabled" in page.locator(
        ".wine-choose__card:has-text('AI Upload')"
    ).get_attribute("class")


@pytest.mark.django_db
def test_ai_upload_is_disabled_by_default(live_server, page, login, user):
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add-choose')}")

    ai_card = page.locator(".wine-choose__card", has_text="AI Upload")
    assert "wine-choose__card--disabled" in ai_card.get_attribute("class")
    assert "need to be configured" in page.locator("main").inner_text()

    page.goto(f"{live_server.url}{reverse('wine-ai-upload')}")
    assert "need to be configured" in page.locator("main").inner_text()
    assert page.locator("#ai-upload-form").count() == 0
