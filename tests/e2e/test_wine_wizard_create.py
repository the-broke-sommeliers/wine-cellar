"""The server-rendered wine creation wizard (WineCreateView,
wine_cellar/apps/wine/views.py:204-296, template wine_create.html) - six
fieldsets toggled by a hidden ``form_step`` field and full-page POSTs per
step, no client-side state machine.

Most tests here pre-create a ``Size`` via factory and pick it as an
*existing* tom-select option, rather than typing a brand new size value -
see ``test_new_size_value_should_survive_wizard_step_navigation`` at the
bottom for why: creating a new size mid-wizard hits a real bug where the
value is silently dropped as soon as you move to another step.
"""

import pytest
from django.urls import reverse

from tests.e2e.conftest import tom_select_pick
from wine_cellar.apps.wine.models import Wine

pytestmark = pytest.mark.e2e


def fill_step_0(
    page, wine_type="Red", country="Germany", size="0.75", name="Chateau Test"
):
    tom_select_pick(page, "id_wine_type", wine_type)
    tom_select_pick(page, "id_country", country)
    tom_select_pick(page, "id_size", size)
    page.locator("#id_name").fill(name)


@pytest.mark.django_db
def test_full_wizard_create_flow_reaches_wine_list(
    live_server, page, login, user, size_factory
):
    size_factory(user=user, name=0.75)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add')}")

    fill_step_0(page, name="Wizard Wine")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_1:not(.hidden)")

    tom_select_pick(page, "id_grapes", "Merlot", create=True)
    page.locator("#id_vintage").fill("2018")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_2:not(.hidden)")

    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_3:not(.hidden)")

    page.locator("#id_price").fill("12.50")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_4:not(.hidden)")

    page.locator("#id_rating").fill("8")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_5:not(.hidden)")

    page.get_by_role("button", name="Save and Finish").click()
    page.wait_for_url(f"**{reverse('wine-list')}")
    assert "Wizard Wine" in page.locator("ul.wine-card__list").inner_text()


@pytest.mark.django_db
def test_back_button_preserves_previously_entered_values(
    live_server, page, login, user, size_factory
):
    size_factory(user=user, name=0.75)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add')}")

    fill_step_0(page, name="Back Button Wine")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_1:not(.hidden)")

    page.locator("#id_vintage").fill("2015")
    page.get_by_role("button", name="Back").click()
    page.wait_for_selector("#create__fs_0:not(.hidden)")
    assert page.locator("#id_name").input_value() == "Back Button Wine"

    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_1:not(.hidden)")
    assert page.locator("#id_vintage").input_value() == "2015"


@pytest.mark.django_db
def test_blank_required_field_blocks_submission(
    live_server, page, login, user, size_factory
):
    """The wizard form carries `novalidate`, but the required inputs (name,
    wine type, country, size) still have the HTML `required` attribute -
    the browser's own "please fill out this field" constraint validation
    stops the click from ever submitting, so the step never advances and no
    request reaches the server at all."""
    size_factory(user=user, name=0.75)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add')}")

    tom_select_pick(page, "id_wine_type", "Red")
    tom_select_pick(page, "id_country", "Germany")
    tom_select_pick(page, "id_size", "0.75")
    # name deliberately left blank
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(300)

    assert page.locator("#create__fs_0:not(.hidden)").count() == 1
    assert page.eval_on_selector("#id_name", "el => el.validity.valid") is False


@pytest.mark.django_db
def test_duplicate_wine_error_should_be_shown_to_the_user(
    live_server, page, login, user, wine_factory, size_factory
):
    """WineCreateView.form_valid() catches the duplicate-wine IntegrityError
    and calls ``form.add_error(None, "...already exists...")`` - a
    *non-field* error. But neither `wine_create.html` nor `wine_edit.html`
    ever render `form.non_field_errors` anywhere, so that message is
    silently swallowed: the user just watches the wizard bounce back to the
    same step with no feedback at all about why nothing was saved. This
    test asserts the obviously-intended behavior (the user is told what
    went wrong) and is expected to fail against that gap."""
    # The uniqueness constraint is on (name, wine_type, abv, size, vintage,
    # country, user) - SQL treats NULL as never equal to NULL, so any NULL
    # column would exempt the row from the constraint entirely. Every field
    # needs a concrete, matching value for the collision to actually fire.
    size = size_factory(user=user, name=0.75)
    wine_factory(
        user=user,
        name="Twin Wine",
        wine_type="RE",
        country="DE",
        vintage=2019,
        abv=13.5,
        size=size,
    )

    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add')}")
    fill_step_0(page, name="Twin Wine")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_1:not(.hidden)")
    page.locator("#id_vintage").fill("2019")
    page.locator("#id_abv").fill("13.5")

    page.get_by_role("button", name="Save and Finish").click()
    page.wait_for_timeout(500)

    # The duplicate is correctly rejected at the data layer either way...
    assert Wine.objects.filter(user=user, name="Twin Wine").count() == 1
    # ...but the user should actually be told that's what happened.
    assert "already exists" in page.locator("main").inner_text()


@pytest.mark.django_db
def test_personal_notes_step_has_no_dead_stock_field(
    live_server, page, login, user, size_factory
):
    """`wine_create.html` includes ``form.stock`` in the Personal Notes
    fieldset, but ``WineForm`` has no ``stock`` field (the ``Wine.stock``
    model field was removed by migration 0010) - Django template lookup
    silently resolves the missing attribute to an empty string, rendering a
    broken, label-only field with no input. The wizard should not show any
    such dead control."""
    size_factory(user=user, name=0.75)
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add')}")
    fill_step_0(page)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_1:not(.hidden)")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_2:not(.hidden)")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_3:not(.hidden)")
    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_4:not(.hidden)")

    notes_step = page.locator("#create__fs_4")
    empty_field_containers = notes_step.locator(
        ".form-container:not(:has(input)):not(:has(textarea)):not(:has(select))"
    )
    assert empty_field_containers.count() == 0, (
        "Personal Notes step renders a form-container with no actual input - "
        "this is the dead `form.stock` reference in wine_create.html."
    )


@pytest.mark.django_db
def test_new_size_value_should_survive_wizard_step_navigation(
    live_server, page, login, user
):
    """A brand new "size" value typed via the create-new tom-select on step
    0 should still be selected after navigating to another step and back -
    exactly like grapes/vineyard/region/appellation/etc. do (see
    ``WineFormPostCleanMixin._post_clean`` re-deriving each field's
    tom-select ``items`` so the client can re-create it on re-render).

    ``wine_cellar/apps/wine/forms.py``'s ``_post_clean`` builds that
    "recreate on re-render" tom-select config only for a fixed tuple of
    field names, and "size" is missing from it (unlike the sibling
    "create new" fields it's grouped with everywhere else in the form) -
    so the freshly typed size is silently dropped as soon as the wizard
    re-renders for the next step. This test documents the correct,
    intended behavior and is expected to fail against that bug."""
    login(user)
    page.goto(f"{live_server.url}{reverse('wine-add')}")

    tom_select_pick(page, "id_wine_type", "Red")
    tom_select_pick(page, "id_country", "Germany")
    tom_select_pick(page, "id_size", "0.75", create=True)
    page.locator("#id_name").fill("New Size Wine")

    page.get_by_role("button", name="Continue").click()
    page.wait_for_selector("#create__fs_1:not(.hidden)")

    # Step 0's fieldset (incl. #id_size) is still in the DOM, just
    # CSS-hidden - its newly-created value should have round-tripped
    # through the re-render along with name/wine_type/country. (Checking
    # for a *non-empty* selected value, not just any selectedOptions entry -
    # with nothing selected, the placeholder `<option value="">` counts as
    # "selected" by default and would give a false pass.)
    assert page.eval_on_selector("#id_size", "el => el.value") == "tom_new_opt0.75", (
        "the newly created size value should still be selected after "
        "the wizard re-renders for the next step"
    )
