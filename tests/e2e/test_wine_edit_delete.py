"""Single-page wine edit (WineUpdateView, wine_edit.html) and delete
confirmation flow (WineDeleteView, wine_confirm_delete.html)."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.e2e


@pytest.mark.django_db
def test_edit_wine_persists_changes(
    live_server, page, login, user, wine_factory, size_factory
):
    # WineFactory leaves `size` unset (nullable FK), but the form's size
    # field is required - without one, the browser's own "required" client
    # validation would block the edit form from submitting at all.
    size = size_factory(user=user, name=0.75)
    wine = wine_factory(user=user, name="Old Name", size=size)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-edit', kwargs={'pk': wine.pk})}")

    page.locator("#id_name").fill("New Name")
    page.locator("#id_price").fill("19.99")
    page.get_by_role("button", name="Save").click()

    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    detail_text = page.locator("main").inner_text()
    assert "New Name" in detail_text
    assert "19.99" in detail_text or "19,99" in detail_text


@pytest.mark.django_db
def test_delete_wine_confirm_flow(live_server, page, login, user, wine_factory):
    wine = wine_factory(user=user, name="Doomed Wine")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-detail', kwargs={'pk': wine.pk})}")

    page.get_by_role("link", name="Delete").click()
    page.wait_for_url(f"**{reverse('wine-delete', kwargs={'pk': wine.pk})}")
    assert "Doomed Wine" in page.locator("main").inner_text()

    page.get_by_role("button", name="Delete").click()
    page.wait_for_url(f"**{reverse('wine-list')}")
    assert "Doomed Wine" not in page.locator("ul.wine-card__list").inner_text()


@pytest.mark.django_db
def test_cancel_delete_leaves_wine_intact(live_server, page, login, user, wine_factory):
    wine = wine_factory(user=user, name="Safe Wine")
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-delete', kwargs={'pk': wine.pk})}")

    page.get_by_role("link", name="Cancel").click()
    page.wait_for_url(f"**{reverse('wine-detail', kwargs={'pk': wine.pk})}")
    assert "Safe Wine" in page.locator("main").inner_text()

    from wine_cellar.apps.wine.models import Wine

    assert Wine.objects.filter(pk=wine.pk).exists()
