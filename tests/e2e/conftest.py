"""Shared fixtures/helpers for the Playwright e2e suite.

Every test in ``tests/e2e/`` gets a logged-in browser session via the
``login`` fixture rather than driving the real login form each time (the
form itself is covered once, thoroughly, in ``test_auth.py``) - this keeps
the rest of the suite fast and focused on the feature under test.

TomSelect (``wine_cellar/assets/js/init_tom_select.ts``) replaces every
plain ``<select>`` on pages that load the ``tom_select`` bundle with a
custom widget, so Playwright's native ``select_option()`` doesn't work
against them. ``tom_select_pick`` drives the rendered widget instead.
"""

from io import BytesIO

import pytest
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore
from PIL import Image


@pytest.fixture
def login(live_server, page):
    """Returns a callable ``login(user)`` that authenticates ``page`` as
    ``user`` by injecting a real Django session cookie, without going
    through the login form UI."""

    def _login(user):
        session = SessionStore()
        session[SESSION_KEY] = str(user.pk)
        session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session.save()
        page.context.add_cookies(
            [
                {
                    "name": settings.SESSION_COOKIE_NAME,
                    "value": session.session_key,
                    "url": live_server.url,
                }
            ]
        )
        return user

    return _login


@pytest.fixture
def small_image_path(tmp_path):
    """Path to a tiny real PNG on disk, for Playwright's ``set_input_files``
    (which needs a filesystem path/buffer, unlike Django's
    ``SimpleUploadedFile`` used by the unit-test suite's
    ``tests/helpers.py:random_png``)."""
    path = tmp_path / "upload.png"
    buf = BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format="PNG")
    path.write_bytes(buf.getvalue())
    return str(path)


def tom_select_pick(page, field_id, text, create=False):
    """Pick (or create) an option by its visible text on a TomSelect-
    enhanced ``<select id="{field_id}">``.

    TomSelect stamps its control element with id ``{field_id}-ts-control``
    (an ``<input>`` when the field has search enabled - the app's "create
    new" tom-selects, e.g. grapes/country/size - or the control ``<div>``
    itself when search is disabled - plain single-choice tom-selects like
    wine type/category) and its dropdown content with
    ``{field_id}-ts-dropdown``.

    Fields that already have options (wine type, country, ...) open their
    dropdown as soon as the control is clicked. Fields that start out with
    *no* options at all (e.g. "size" for a user with no sizes yet) don't -
    there's nothing to show until a search term narrows/creates something -
    so for the input variant we type first and only then wait for the
    dropdown, rather than requiring it to already be open.

    Filtered with ``:visible`` throughout because ``wine_list.html`` (and
    similarly duplicated filter forms) renders the *same* filter form twice
    for the small/large-screen layouts, toggled by CSS media queries alone -
    both copies get real ids and their own TomSelect instance, so a bare
    ``#field_id`` would match two elements and only one is ever actually
    interactable at the current viewport size.
    """
    control = page.locator(f"#{field_id}-ts-control:visible")
    control.click()
    dropdown = page.locator(f"#{field_id}-ts-dropdown:visible")

    if control.evaluate("el => el.tagName") == "INPUT":
        control.fill(text)

    dropdown.wait_for(state="visible")

    if create:
        option = dropdown.locator(".create", has_text=text).first
        if option.count() == 0:
            option = dropdown.locator(".option", has_text=text).first
    else:
        option = dropdown.locator(".option", has_text=text).first
    option.click()
    dropdown.wait_for(state="hidden")
    # Large-option-set tom-selects (maxOptions: null, e.g. country/region/
    # appellation/size) can spontaneously reopen their dropdown for a moment
    # within roughly a second of a selection - seemingly an internal
    # re-render finishing late on a big option list. Left open, it
    # physically overlaps whatever comes next in the form and swallows its
    # click, so give it a moment to settle and nudge it closed if needed.
    page.wait_for_timeout(500)
    if dropdown.is_visible():
        page.keyboard.press("Escape")
        dropdown.wait_for(state="hidden")


def tom_select_selected_text(page, field_id):
    """Return the visible text of the currently selected item(s) on a
    TomSelect-enhanced select, for asserting persisted values."""
    field = page.locator(f"#{field_id}")
    wrapper = field.locator(
        "xpath=following-sibling::*[contains(concat(' ', "
        "normalize-space(@class), ' '), ' ts-wrapper ')][1]"
    )
    return wrapper.locator(".item").all_inner_texts()
