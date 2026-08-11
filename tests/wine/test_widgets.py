from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.utils.html import escape

from wine_cellar.apps.wine.widgets import MapChoosePointWidget


def test_render_raises_when_bundle_missing():
    """If the frontend build hasn't generated the `react_choose_point`
    bundle, fail loudly instead of silently rendering a broken widget."""
    widget = MapChoosePointWidget(polygon=None)
    with patch("wine_cellar.apps.wine.widgets.get_files", return_value=[]):
        with pytest.raises(ImproperlyConfigured):
            widget.render("location", None, {})


def test_render_includes_existing_point_value():
    """A wine that already has a saved location must have it preloaded
    into the widget's hidden input on the edit form."""
    widget = MapChoosePointWidget(polygon=None)
    point = '{"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}}'
    with patch(
        "wine_cellar.apps.wine.widgets.get_files",
        return_value=[{"name": "react_choose_point.js"}],
    ):
        html = widget.render("location", point, {})
    assert f'value="{escape(point)}"' in html


def test_render_value_null_string_skips_point():
    """The literal string `"null"` (sent by the frontend when no point is
    selected) must not be treated as a real point value."""
    widget = MapChoosePointWidget(polygon=None)
    with patch(
        "wine_cellar.apps.wine.widgets.get_files",
        return_value=[{"name": "react_choose_point.js"}],
    ):
        html = widget.render("location", "null", {})
    assert "value=" not in html


def test_render_no_value_skips_point():
    widget = MapChoosePointWidget(polygon=None)
    with patch(
        "wine_cellar.apps.wine.widgets.get_files",
        return_value=[{"name": "react_choose_point.js"}],
    ):
        html = widget.render("location", None, {})
    assert "value=" not in html
